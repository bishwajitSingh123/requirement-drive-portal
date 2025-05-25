from django.utils import timezone
from django.http import HttpRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from application_tracking.enums import ApplicationStatus
from common.tasks import send_email
from accounts.models import User
from django.db.models import Q
from .models import JobAdvert, JobApplication
from .forms import jobAdvertForm, JobApplicationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator

# Create your views here.
@login_required
def create_advert(request:HttpRequest):
    form = jobAdvertForm(request.POST or None)

    if form.is_valid():
        instance: JobAdvert = form.save(commit=False)
        instance.created_by = request.user
        instance.save()
        messages.success(request, "Advert created. You can now recieve applications.")
        return redirect(instance.get_absolute_url())

    context = {
        "job_advert_form": form,
        "title": "Create a new advert",
        "btn_text": "Create advert"
    }
    return render(request, "create_advert.html", context)



def list_advert(request:HttpRequest):
    active_jobs = JobAdvert.objects.active()

    paginator = Paginator(active_jobs, 10)
    requested_page = request.GET.get("page")
    paginated_adverts = paginator.get_page(requested_page)

    context = {
        "job_adverts": paginated_adverts
    }
    return render(request, "home.html", context)



def get_advert(request:HttpRequest, advert_id):
    form = JobApplicationForm()
    job_advert = get_object_or_404(JobAdvert, pk=advert_id)
    context = {
        "job_advert":job_advert,
        "application_form":form,
    }
    return render(request, "advert.html", context)

@login_required
def update_advert(request:HttpRequest, advert_id):
    advert: JobAdvert = get_object_or_404(JobAdvert, pk=advert_id)
    if request.user != advert.created_by:
        return HttpResponseForbidden("You can only update an advert created by you.")
    form = jobAdvertForm(request.POST or None, instance=advert)
    if form.is_valid():
        instance: JobAdvert = form.save(commit=False)
        instance.save()
        messages.success(request, "Advert updated successfully.")
        return redirect(instance.get_absolute_url())
    
    context = {
        "job_advert_form":form,
        "btn":"Update advert"
    }
    return render(request, "create_advert.html", context)

@login_required
def delete_advert(request: HttpRequest, advert_id):
    advert: JobAdvert =get_object_or_404(JobAdvert, pk=advert_id)
    if request.user != advert.created_by:
        return HttpResponseForbidden("You can only delete an advert created byv you.")
    
    advert.delete()
    messages.success(request, "Advert deleted successfully.")
    return redirect("my_jobs")
    


def apply(request:HttpRequest, advert_id):
    advert = get_object_or_404(JobAdvert, pk=advert_id)
    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid(): 
            # prevent duplicate applications for same email
            email = form.cleaned_data['email']
            if advert.applications.filter(email__iexact=email).exists():
                messages.error(request, "You have already applied for this position")
                return redirect("job_advert", advert_id=advert_id)
            
            #save the application
            application: JobApplication = form.save(commit=False)
            application.job_advert = advert
            application.save()
            messages.success(request, "Application submitted succesfully")
            return redirect("job_advert", advert_id=advert_id)
    else:
        form = JobApplicationForm()
        context = {
            "job_advert": advert,
            "applications": form 
        }
        return render(request, "advert.html", context)


@login_required
def my_applications(request: HttpRequest):
    user:User = request.user
    appllications = JobApplication.objects.filter(email=user.email)
    paginator = Paginator(appllications, 10)
    
    requested_page = request.GET.get("page")
    paginated_applications = paginator.get_page(requested_page)

    context = {
        "my_applications": paginated_applications
    }
    return render(request, "my_applications.html", context)


@login_required
def my_jobs(request: HttpRequest):
    user:User = request.user
    jobs = JobAdvert.objects.filter(created_by=user)
    paginator = Paginator(jobs, 10)
    requested_page = request.GET.get("page")
    paginated_jobs = paginator.get_page(requested_page)

    context = {
        "my_jobs": paginated_jobs,
        "current_date":timezone.now().date()
    }
    return render(request, "my_jobs.html", context)

@login_required
def advert_applications(request:HttpRequest, advert_id):
    advert: JobAdvert = get_object_or_404(JobAdvert, pk=advert_id)
    if request.user != advert.created_by:
        return HttpResponseForbidden("You can only see the applications for the advert created by you.")
    
    application = advert.applications.all()
    pagianator = Paginator(application, 10)
    requested_page = request.GET.get("page")
    paginated_applications = pagianator.get_page(requested_page)

    context = {
        "applications":paginated_applications,
        "advert":advert
    }
    return render(request, "advert_applications.html", context)

@login_required
def decide(request: HttpRequest, job_application_id):
    job_application: JobApplication = get_object_or_404(JobApplication, pk=job_application_id)

    if request.user != job_application.job_advert.created_by:
        return HttpResponseForbidden("You can only decide on the advert created by You Mr.")
    
    if request.method == "POST":
        status = request.POST.get("status")
        job_application.status = status
        job_application.save(update_fields=["status"])
        messages.success(request, f"Application status updated to {status}")

        if status == ApplicationStatus.REJECTED:
            context = {
                "applicant_name":job_application.name,
                "job_title":job_application.job_advert.title,
                "company_name":job_application.job_advert.company_name
            }
         
            send_email(
                f"Application Outcome for {job_application.job_advert.title}",
                [job_application.email],
                "emails/job_application_update.html",
                context
            )
        return redirect("advert_applications", advert_id=job_application.job_advert.id)
    

def search(request: HttpRequest):
    keyword = request.GET.get("keyword")
    location = request.GET.get("location")

    # query = Q()

    # if keyword:
    #     query &= (
    #         Q(title__icontains=keyword)
    #         | Q(company_name__icontains=keyword)
    #         | Q(description__icontains=keyword)
    #         | Q(skills__icontains=keyword)
    #     )
    # if location:
    #     query &= Q(location__icontains=location)


    # active_jobs = JobAdvert.objects.filter(is_published=True, deadline__gte=timezone.now().date())
    
    # result = active_jobs.filter(query)
    result = JobAdvert.objects.search(keyword, location)
    paginator = Paginator(result, 10)
    requested_page = request.GET.get("page")
    paginated_adverts = paginator.get_page(requested_page)

    context = {
        "job_adverts": paginated_adverts
    }
    return render(request, "home.html", context)
