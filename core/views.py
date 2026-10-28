"""
Views for the core app — dashboard and health check.
"""
from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from billing.models import Invoice, InvoiceStatus, Payment, PaymentStatus
from customers.models import Customer
from projects.models import Project, ProjectStatus


class DashboardView(LoginRequiredMixin, View):
    """
    Main dashboard for an authenticated artist.
    Aggregates metrics and recent activity strictly scoped to request.user.
    """
    template_name = "core/dashboard.html"

    def get(self, request):
        user = request.user
        default_currency = user.artist_profile.default_currency if hasattr(user, "artist_profile") else "USD"

        # 1. Invoices scoped to artist
        artist_invoices = Invoice.objects.filter(artist=user)
        issued_invoices = artist_invoices.filter(
            status__in=[InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]
        )

        outstanding_balance = sum((inv.balance_due for inv in issued_invoices), Decimal("0.00"))

        # 2. Confirmed payments
        succeeded_payments = Payment.objects.filter(artist=user, status=PaymentStatus.SUCCEEDED)
        confirmed_payments_total = succeeded_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # 3. Active projects
        active_projects_count = Project.objects.filter(
            artist=user,
            status__in=[ProjectStatus.INQUIRY, ProjectStatus.ACCEPTED, ProjectStatus.IN_PROGRESS],
        ).count()

        # 4. Overdue invoices
        today = timezone.now().date()
        overdue_invoices_count = issued_invoices.filter(
            due_date__lt=today
        ).count()

        # 5. Recent items
        recent_projects = Project.objects.filter(artist=user).select_related("customer")[:5]
        recent_invoices = artist_invoices.select_related("customer")[:5]
        has_customers = Customer.objects.filter(artist=user).exists()

        context = {
            "currency": default_currency,
            "has_customers": has_customers,
            "metrics": [
                {
                    "label": "Outstanding balance",
                    "value": f"{outstanding_balance:,.2f} {default_currency}",
                    "icon": "💳",
                    "description": "Uncollected receivables",
                    "url_name": "billing:invoice_list",
                },
                {
                    "label": "Confirmed payments",
                    "value": f"{confirmed_payments_total:,.2f} {default_currency}",
                    "icon": "✅",
                    "description": "Total settled revenue",
                    "url_name": "billing:payment_list",
                },
                {
                    "label": "Active commissions",
                    "value": str(active_projects_count),
                    "icon": "🎨",
                    "description": "Inquiry, accepted, or in progress",
                    "url_name": "projects:list",
                },
                {
                    "label": "Overdue invoices",
                    "value": str(overdue_invoices_count),
                    "icon": "⚠️",
                    "description": "Invoices past due date",
                    "url_name": "billing:invoice_list",
                },
            ],
            "recent_projects": recent_projects,
            "recent_invoices": recent_invoices,
        }
        return render(request, self.template_name, context)


class HealthView(View):
    """
    Health check endpoint — no authentication required.
    Returns JSON {"status": "ok"} for uptime monitors and deployment checks.
    """

    def get(self, request):
        return JsonResponse({"status": "ok"})
