"""
Views for Invoices, Payments, and Public Customer Payment/Receipt flows.
"""

import hmac
import hashlib
import json
import logging
import uuid
from decimal import Decimal
from django.utils import timezone
from decouple import config
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import DetailView, ListView, View

from customers.models import Customer
from projects.models import Project
from .models import Invoice, Payment, InvoiceStatus, PaymentStatus

from .forms import InvoiceForm, InvoiceLineFormSet, ManualPaymentForm
from .services import PaystackService, notify_artist_payment_received, notify_artist_payment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Artist-Authenticated Invoice Views
# ---------------------------------------------------------------------------


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "billing/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 25

    def get_queryset(self):
        qs = Invoice.objects.filter(artist=self.request.user).select_related(
            "customer", "project"
        )
        status_filter = self.request.GET.get("status")
        if status_filter in dict(InvoiceStatus.choices):
            qs = qs.filter(status=status_filter)

        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(invoice_number__icontains=query)
                | Q(customer__name__icontains=query)
                | Q(project__title__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_status"] = self.request.GET.get("status", "")
        context["query"] = self.request.GET.get("q", "")
        context["statuses"] = InvoiceStatus.choices
        context["all_count"] = Invoice.objects.filter(artist=self.request.user).count()
        return context


class InvoiceCreateView(LoginRequiredMixin, View):
    template_name = "billing/invoice_form.html"

    def get(self, request):
        initial = {}
        customer_id = request.GET.get("customer")
        if customer_id:
            customer = Customer.objects.filter(
                pk=customer_id, artist=request.user
            ).first()
            if customer:
                initial["customer"] = customer

        project_id = request.GET.get("project")
        if project_id:
            project = Project.objects.filter(pk=project_id, artist=request.user).first()
            if project:
                initial["project"] = project
                if not initial.get("customer"):
                    initial["customer"] = project.customer

        form = InvoiceForm(artist=request.user, initial=initial)
        formset = InvoiceLineFormSet(prefix="lines")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "is_create": True,
            },
        )

    def post(self, request):
        form = InvoiceForm(request.POST, artist=request.user)
        formset = InvoiceLineFormSet(request.POST, prefix="lines")

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = form.save(commit=False)
                invoice.artist = request.user
                invoice.status = InvoiceStatus.DRAFT
                invoice.save()

                formset.instance = invoice
                formset.save()

                # Calculate line totals and invoice totals
                invoice.calculate_totals(save=True)

            messages.success(
                request, f"Invoice draft '{invoice.invoice_number}' created."
            )
            return redirect(
                reverse("billing:invoice_detail", kwargs={"pk": invoice.pk})
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "is_create": True,
            },
        )


class InvoiceUpdateView(LoginRequiredMixin, View):
    template_name = "billing/invoice_form.html"

    def get_object(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, artist=request.user)
        if invoice.status != InvoiceStatus.DRAFT:
            messages.error(request, "Only draft invoices can be edited.")
        return invoice

    def get(self, request, pk):
        invoice = self.get_object(request, pk)
        if invoice.status != InvoiceStatus.DRAFT:
            return redirect(
                reverse("billing:invoice_detail", kwargs={"pk": invoice.pk})
            )

        form = InvoiceForm(instance=invoice, artist=request.user)
        formset = InvoiceLineFormSet(instance=invoice, prefix="lines")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "invoice": invoice,
                "is_create": False,
            },
        )

    def post(self, request, pk):
        invoice = self.get_object(request, pk)
        if invoice.status != InvoiceStatus.DRAFT:
            return redirect(
                reverse("billing:invoice_detail", kwargs={"pk": invoice.pk})
            )

        form = InvoiceForm(request.POST, instance=invoice, artist=request.user)
        formset = InvoiceLineFormSet(request.POST, instance=invoice, prefix="lines")

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = form.save()
                formset.save()
                invoice.calculate_totals(save=True)

            messages.success(request, f"Invoice '{invoice.invoice_number}' updated.")
            return redirect(
                reverse("billing:invoice_detail", kwargs={"pk": invoice.pk})
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "invoice": invoice,
                "is_create": False,
            },
        )


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "billing/invoice_detail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return Invoice.objects.filter(artist=self.request.user).select_related(
            "customer", "project"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.object
        context["lines"] = invoice.lines.all()
        context["payments"] = invoice.payments.all()
        context["payment_form"] = ManualPaymentForm(initial={"amount": invoice.balance_due})
        if invoice.public_token:
            context["public_url"] = self.request.build_absolute_uri(
                reverse(
                    "billing:public_invoice", kwargs={"token": invoice.public_token}
                )
            )
        return context


class InvoiceIssueView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, artist=request.user)
        if invoice.status != InvoiceStatus.DRAFT:
            messages.warning(
                request, "This invoice is already issued or cannot be issued."
            )
            return redirect(
                reverse("billing:invoice_detail", kwargs={"pk": invoice.pk})
            )

        if not invoice.lines.exists():
            messages.error(request, "Cannot issue an invoice with no line items.")
            return redirect(
                reverse("billing:invoice_detail", kwargs={"pk": invoice.pk})
            )

        invoice.issue()
        
        # Trigger SMS notification to customer if phone number is present
        if invoice.customer and invoice.customer.phone_number:
            public_url = request.build_absolute_uri(
                reverse("billing:public_invoice", kwargs={"token": invoice.public_token})
            )
            message = f"Hello {invoice.customer.name}, you have a new invoice from {invoice.artist.get_full_name()}. View here: {public_url}"
            try:
                from communications.services import send_sms
                send_sms(invoice.customer.phone_number, message)
            except Exception as e:
                logger.warning(f"Customer invoice issue SMS could not be sent: {e}")

        messages.success(
            request,
            f"Invoice '{invoice.invoice_number}' has been issued! A private customer link is ready.",
        )
        return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))


class InvoiceVoidView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, artist=request.user)
        if invoice.status == InvoiceStatus.PAID:
            messages.error(request, "Cannot void an already paid invoice.")
            return redirect(
                reverse("billing:invoice_detail", kwargs={"pk": invoice.pk})
            )

        invoice.void()
        messages.success(
            request,
            f"Invoice '{invoice.invoice_number}' has been marked as VOID. Public link is now revoked.",
        )
        return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))


class InvoiceRecordPaymentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, artist=request.user)
        if invoice.status == InvoiceStatus.VOID:
            messages.error(request, "Cannot record payment on a voided invoice.")
            return redirect(
                reverse("billing:invoice_detail", kwargs={"pk": invoice.pk})
            )

        form = ManualPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.artist = request.user
            payment.invoice = invoice
            payment.currency = invoice.currency
            payment.provider = "manual"
            payment.provider_reference = f"MAN-{uuid.uuid4().hex[:8].upper()}"
            payment.status = PaymentStatus.SUCCEEDED
            payment.save()

            messages.success(request, f"Payment of {payment.amount} {payment.currency} recorded.")
        else:
            messages.error(request, "Error recording payment. Please check the amount.")

        return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))


class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = "billing/payment_list.html"
    context_object_name = "payments"
    paginate_by = 25

    def get_queryset(self):
        return Payment.objects.filter(artist=self.request.user).select_related(
            "invoice", "invoice__customer"
        )


# ---------------------------------------------------------------------------
# Public Customer Invoice, Payment & Receipt Views (No Auth Required)
# ---------------------------------------------------------------------------


class PublicInvoiceView(View):
    template_name = "billing/public_invoice.html"

    def get(self, request, token):
        invoice = (
            Invoice.objects.filter(public_token=token)
            .select_related("artist", "artist__artist_profile", "customer", "project")
            .first()
        )

        if not invoice or invoice.status in [InvoiceStatus.DRAFT, InvoiceStatus.VOID]:
            return render(
                request,
                "billing/public_revoked.html",
                {
                    "is_void": invoice and invoice.status == InvoiceStatus.VOID,
                },
                status=404,
            )

        return render(request, self.template_name, {
            "invoice": invoice,
            "lines": invoice.lines.all(),
            "payments": invoice.payments.filter(status=PaymentStatus.SUCCEEDED),
            "token": token,
        })


class PublicPaymentView(View):
    template_name = "billing/public_payment.html"

    def get_invoice(self, token):
        invoice = (
            Invoice.objects.filter(public_token=token)
            .select_related("artist", "artist__artist_profile", "customer")
            .first()
        )
        if not invoice or invoice.status in [InvoiceStatus.DRAFT, InvoiceStatus.VOID]:
            raise Http404("Invoice not found or expired.")
        return invoice

    def get(self, request, token):
        invoice = self.get_invoice(token)
        if invoice.balance_due <= Decimal("0.00"):
            return redirect(reverse("billing:public_receipt", kwargs={"token": token}))

        return render(request, self.template_name, {
            "invoice": invoice,
            "token": token,
            "suggested_amount": invoice.balance_due,
        })

    def post(self, request, token):
        invoice = self.get_invoice(token)
        if invoice.balance_due <= Decimal("0.00"):
            return redirect(reverse("billing:public_receipt", kwargs={"token": token}))

        raw_amount = request.POST.get("amount")
        try:
            amount = Decimal(raw_amount)
            if amount <= Decimal("0.00"):
                raise ValueError()
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid payment amount greater than zero.")
            return render(request, self.template_name, {
                "invoice": invoice,
                "token": token,
                "suggested_amount": invoice.balance_due,
            })

        payment_method = request.POST.get("payment_method", "Credit Card (Demo Simulator)")

        is_mock = (
            request.POST.get("action") == "mock_pay"
            or request.POST.get("mock_pay")
            or "demo" in payment_method.lower()
            or "mock" in payment_method.lower()
            or "simulator" in payment_method.lower()
            or (request.POST.get("action") != "paystack" and not PaystackService.SECRET_KEY)
        )

        if is_mock:
            with transaction.atomic():
                payment = Payment.objects.create(
                    artist=invoice.artist,
                    invoice=invoice,
                    provider="mock_demo",
                    provider_reference=f"MOCK-{uuid.uuid4().hex[:10].upper()}",
                    amount=amount,
                    currency=invoice.currency,
                    status=PaymentStatus.SUCCEEDED,
                    payment_method=payment_method or "Mock Payment Simulator",
                    notes="Payment completed via customer mock payment simulator.",
                )

            # Trigger SMS notification to artist
            sms_sent, artist_notice = notify_artist_payment_received(payment)

            # Trigger SMS notification to customer if phone exists
            customer = invoice.customer
            if customer and customer.phone_number:
                try:
                    from communications.services import send_sms
                    send_sms(
                        customer.phone_number,
                        f"Thank you {customer.name}! Your payment of {payment.amount} {payment.currency} has been confirmed.",
                    )
                except Exception as e:
                    logger.warning(f"Customer SMS error: {e}")

            messages.success(
                request,
                f"Demo payment of {payment.amount} {payment.currency} succeeded! {artist_notice}",
            )
            return redirect(reverse("billing:public_receipt", kwargs={"token": token}))

        # Create a pending payment record for Paystack
        with transaction.atomic():
            payment = Payment.objects.create(
                artist=invoice.artist,
                invoice=invoice,
                provider="paystack",
                provider_reference=f"PYST-{uuid.uuid4().hex[:10].upper()}",
                amount=amount,
                currency=invoice.currency,
                status=PaymentStatus.PENDING,
                payment_method=payment_method,
                notes="Payment initiated via Paystack.",
            )

        # Paystack expects amount in the smallest currency unit (e.g., cents/kobo)
        paystack_amount = int(amount * 100)
        
        customer_email = invoice.customer.email or "customer@example.com"
        callback_url = request.build_absolute_uri(
            reverse("billing:public_receipt", kwargs={"token": token})
        )
        
        auth_url = PaystackService.initialize_transaction(
            email=customer_email,
            amount=paystack_amount,
            callback_url=callback_url,
            metadata={"payment_id": str(payment.id), "invoice_id": str(invoice.id)}
        )

        if auth_url:
            return redirect(auth_url)
        else:
            messages.error(request, "Could not initialize payment with Paystack. Please try again or use the Mock Payment option.")
            return render(request, self.template_name, {
                "invoice": invoice,
                "token": token,
                "suggested_amount": invoice.balance_due,
            })


@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhookView(View):
    """
    Webhook handler for Paystack events.
    """
    def post(self, request):
        signature = request.headers.get("X-Paystack-Signature")
        if not signature:
            return HttpResponse("Missing signature", status=400)

        # Verify signature
        secret = config("PAYSTACK_SECRET_KEY", default="")
        payload = request.body
        expected_signature = hmac.new(
            secret.encode("utf-8"), 
            payload, 
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            return HttpResponse("Invalid signature", status=400)

        try:
            data = json.loads(payload)
            event = data.get("event")
            
            if event == "charge.success":
                payment_data = data.get("data")
                reference = payment_data.get("reference")
                
                payment_id = payment_data.get("metadata", {}).get("payment_id")
                
                if payment_id:
                    with transaction.atomic():
                        payment = Payment.objects.select_for_update().get(id=payment_id)
                        if payment.status == PaymentStatus.PENDING:
                            payment.status = PaymentStatus.SUCCEEDED
                            payment.provider_reference = reference
                            payment.confirmed_at = timezone.now()
                            payment.save()
                            
                            # Update the invoice
                            payment.invoice.update_payment_status()
                            
                            # Trigger SMS notifications
                            customer = payment.invoice.customer
                            if customer and customer.phone_number:
                                message = f"Thank you {customer.name}! Your payment of {payment.amount} {payment.currency} has been confirmed."
                                try:
                                    from communications.services import send_sms
                                    send_sms(customer.phone_number, message)
                                except Exception as sms_err:
                                    logger.warning(f"Paystack customer SMS error: {sms_err}")

                            notify_artist_payment_received(payment)
                            
                return HttpResponse("OK", status=200)

            return HttpResponse("Event ignored", status=200)

        except Exception as e:
            logger.error(f"Paystack webhook error: {e}")
            return HttpResponse("Internal error", status=500)


class PublicReceiptView(View):

    template_name = "billing/public_receipt.html"

    def get(self, request, token):
        invoice = (
            Invoice.objects.filter(public_token=token)
            .select_related("artist", "artist__artist_profile", "customer")
            .first()
        )

        if not invoice:
            raise Http404("Receipt not found.")

        payments = invoice.payments.filter(status=PaymentStatus.SUCCEEDED).order_by(
            "-confirmed_at"
        )
        if not payments.exists():
            return redirect(reverse("billing:public_invoice", kwargs={"token": token}))

        latest_payment = payments.first()

        return render(
            request,
            self.template_name,
            {
                "invoice": invoice,
                "payments": payments,
                "latest_payment": latest_payment,
                "token": token,
            },
        )
