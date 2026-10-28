"""
URL patterns for billing app.
"""
from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    # Artist invoice management
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/new/", views.InvoiceCreateView.as_view(), name="invoice_create"),
    path("invoices/<uuid:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<uuid:pk>/edit/", views.InvoiceUpdateView.as_view(), name="invoice_edit"),
    path("invoices/<uuid:pk>/issue/", views.InvoiceIssueView.as_view(), name="invoice_issue"),
    path("invoices/<uuid:pk>/void/", views.InvoiceVoidView.as_view(), name="invoice_void"),
    path("invoices/<uuid:pk>/record-payment/", views.InvoiceRecordPaymentView.as_view(), name="invoice_record_payment"),

    # Artist payments list
    path("payments/", views.PaymentListView.as_view(), name="payment_list"),

    # Public customer routes
    path("i/<str:token>/", views.PublicInvoiceView.as_view(), name="public_invoice"),
    path("i/<str:token>/pay/", views.PublicPaymentView.as_view(), name="public_payment"),
    path("receipt/<str:token>/", views.PublicReceiptView.as_view(), name="public_receipt"),
]
