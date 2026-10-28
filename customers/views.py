"""
Views for Customer management.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from .forms import CustomerForm
from .models import Customer


class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = "customers/customer_list.html"
    context_object_name = "customers"
    paginate_by = 25

    def get_queryset(self):
        qs = Customer.objects.filter(artist=self.request.user)
        show_archived = self.request.GET.get("archived") == "1"
        if show_archived:
            qs = qs.archived()
        else:
            qs = qs.active()

        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone_number__icontains=query)
                | Q(notes__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        context["show_archived"] = self.request.GET.get("archived") == "1"
        context["active_count"] = Customer.objects.filter(artist=self.request.user).active().count()
        context["archived_count"] = Customer.objects.filter(artist=self.request.user).archived().count()
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = "customers/customer_detail.html"
    context_object_name = "customer"

    def get_queryset(self):
        return Customer.objects.filter(artist=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        context["projects"] = customer.projects.all()
        context["invoices"] = customer.invoices.all()
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"

    def form_valid(self, form):
        form.instance.artist = self.request.user
        messages.success(self.request, f"Customer '{form.instance.name}' created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("customers:detail", kwargs={"pk": self.object.pk})


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"

    def get_queryset(self):
        return Customer.objects.filter(artist=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, f"Customer '{form.instance.name}' updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("customers:detail", kwargs={"pk": self.object.pk})


class CustomerArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk, artist=request.user)
        if customer.is_archived:
            customer.unarchive()
            messages.success(request, f"Customer '{customer.name}' restored.")
        else:
            customer.archive()
            messages.success(request, f"Customer '{customer.name}' archived.")
        return redirect(reverse("customers:detail", kwargs={"pk": customer.pk}))
