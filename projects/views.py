"""
Views for Project management.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from customers.models import Customer
from .forms import ProjectForm
from .models import Project, ProjectStatus


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"
    paginate_by = 25

    def get_queryset(self):
        qs = Project.objects.filter(artist=self.request.user).select_related("customer")
        status_filter = self.request.GET.get("status")
        if status_filter in dict(ProjectStatus.choices):
            qs = qs.filter(status=status_filter)

        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(customer__name__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_status"] = self.request.GET.get("status", "")
        context["query"] = self.request.GET.get("q", "")
        context["statuses"] = ProjectStatus.choices
        context["all_count"] = Project.objects.filter(artist=self.request.user).count()
        return context


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "projects/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return Project.objects.filter(artist=self.request.user).select_related("customer")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoices"] = self.object.invoices.all()
        context["statuses"] = ProjectStatus.choices
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["artist"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        customer_id = self.request.GET.get("customer")
        if customer_id:
            customer = Customer.objects.filter(pk=customer_id, artist=self.request.user).first()
            if customer:
                initial["customer"] = customer
        return initial

    def form_valid(self, form):
        form.instance.artist = self.request.user
        messages.success(self.request, f"Project '{form.instance.title}' created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("projects:detail", kwargs={"pk": self.object.pk})


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    def get_queryset(self):
        return Project.objects.filter(artist=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["artist"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Project '{form.instance.title}' updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("projects:detail", kwargs={"pk": self.object.pk})


class ProjectStatusUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, artist=request.user)
        new_status = request.POST.get("status")
        if new_status in dict(ProjectStatus.choices):
            project.status = new_status
            project.save()
            messages.success(request, f"Project status changed to '{project.get_status_display()}'.")
        return redirect(reverse("projects:detail", kwargs={"pk": project.pk}))
