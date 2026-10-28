"""
Views for Invoices, Payments, and Public Customer Payment/Receipt flows.
"""
from decimal import Decimal
import uuid

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
from .forms import InvoiceForm, InvoiceLineFormSet, ManualPaymentForm
from .models import Invoice, InvoiceLine, InvoiceStatus, Payment, PaymentStatus


# ---------------------------------------------------------------------------
# Artist-Authenticated Invoice Views
# ---------------------------------------------------------------------------

class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "billing/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 25

    def get_queryset(self):
        qs = Invoice.objects.filter(artist=self.request.user).select_related("customer", "project")
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
            customer = Customer.objects.filter(pk=customer_id, artist=request.user).first()
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
        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "is_create": True,
        })

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

            messages.success(request, f"Invoice draft '{invoice.invoice_number}' created.")
            return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))

        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "is_create": True,
        })


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
            return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))

        form = InvoiceForm(instance=invoice, artist=request.user)
        formset = InvoiceLineFormSet(instance=invoice, prefix="lines")
        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "invoice": invoice,
            "is_create": False,
        })

    def post(self, request, pk):
        invoice = self.get_object(request, pk)
        if invoice.status != InvoiceStatus.DRAFT:
            return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))

        form = InvoiceForm(request.POST, instance=invoice, artist=request.user)
        formset = InvoiceLineFormSet(request.POST, instance=invoice, prefix="lines")

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = form.save()
                formset.save()
                invoice.calculate_totals(save=True)

            messages.success(request, f"Invoice '{invoice.invoice_number}' updated.")
            return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))

        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "invoice": invoice,
            "is_create": False,
        })


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "billing/invoice_detail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return Invoice.objects.filter(artist=self.request.user).select_related("customer", "project")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.object
        context["lines"] = invoice.lines.all()
        context["payments"] = invoice.payments.all()
        context["payment_form"] = ManualPaymentForm(initial={"amount": invoice.balance_due})
        if invoice.public_token:
            context["public_url"] = self.request.build_absolute_uri(
                reverse("billing:public_invoice", kwargs={"token": invoice.public_token})
            )
        return context


class InvoiceIssueView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, artist=request.user)
        if invoice.status != InvoiceStatus.DRAFT:
            messages.warning(request, "This invoice is already issued or cannot be issued.")
            return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))

        if not invoice.lines.exists():
            messages.error(request, "Cannot issue an invoice with no line items.")
            return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))

        invoice.issue()
        messages.success(request, f"Invoice '{invoice.invoice_number}' has been issued! A private customer link is ready.")
        return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))


class InvoiceVoidView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, artist=request.user)
        if invoice.status == InvoiceStatus.PAID:
            messages.error(request, "Cannot void an already paid invoice.")
            return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))

        invoice.void()
        messages.success(request, f"Invoice '{invoice.invoice_number}' has been marked as VOID. Public link is now revoked.")
        return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))


class InvoiceRecordPaymentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, artist=request.user)
        if invoice.status == InvoiceStatus.VOID:
            messages.error(request, "Cannot record payment on a voided invoice.")
            return redirect(reverse("billing:invoice_detail", kwargs={"pk": invoice.pk}))

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
        return Payment.objects.filter(artist=self.request.user).select_related("invoice", "invoice__customer")


# ---------------------------------------------------------------------------
# Public Customer Invoice, Payment & Receipt Views (No Auth Required)
# ---------------------------------------------------------------------------

class PublicInvoiceView(View):
    template_name = "billing/public_invoice.html"

    def get(self, request, token):
        invoice = Invoice.objects.filter(public_token=token).select_related(
            "artist", "artist__artist_profile", "customer", "project"
        ).first()

        if not invoice or invoice.status in [InvoiceStatus.DRAFT, InvoiceStatus.VOID]:
            return render(request, "billing/public_revoked.html", {
                "is_void": invoice and invoice.status == InvoiceStatus.VOID,
            }, status=404)

        return render(request, self.template_name, {
            "invoice": invoice,
            "lines": invoice.lines.all(),
            "payments": invoice.payments.filter(status=PaymentStatus.SUCCEEDED),
            "token": token,
        })


class PublicPaymentView(View):
    template_name = "billing/public_payment.html"

    def get_invoice(self, token):
        invoice = Invoice.objects.filter(public_token=token).select_related(
            "artist", "artist__artist_profile", "customer"
        ).first()
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

        payment_method = request.POST.get("payment_method", "Credit Card (Sandbox Demo)")

        with transaction.atomic():
            payment = Payment.objects.create(
                artist=invoice.artist,
                invoice=invoice,
                provider="demo_stub",
                provider_reference=f"DEMO-{uuid.uuid4().hex[:10].upper()}",
                amount=amount,
                currency=invoice.currency,
                status=PaymentStatus.SUCCEEDED,
                payment_method=payment_method,
                notes="Payment completed via Stage 2 customer sandbox stub.",
            )

        messages.success(request, f"Demo payment of {payment.amount} {payment.currency} succeeded!")
        return redirect(reverse("billing:public_receipt", kwargs={"token": token}))


class PublicReceiptView(View):
    template_name = "billing/public_receipt.html"

    def get(self, request, token):
        invoice = Invoice.objects.filter(public_token=token).select_related(
            "artist", "artist__artist_profile", "customer"
        ).first()

        if not invoice:
            raise Http404("Receipt not found.")

        payments = invoice.payments.filter(status=PaymentStatus.SUCCEEDED).order_by("-confirmed_at")
        if not payments.exists():
            return redirect(reverse("billing:public_invoice", kwargs={"token": token}))

        latest_payment = payments.first()

        return render(request, self.template_name, {
            "invoice": invoice,
            "payments": payments,
            "latest_payment": latest_payment,
            "token": token,
        })
