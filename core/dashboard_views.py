from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from accounts.decorators import role_required
from .models import ErrorLog


@role_required('admin', 'teacher')
def error_list(request):
    errors   = ErrorLog.objects.filter(resolved=False).select_related('user')[:100]
    resolved = ErrorLog.objects.filter(resolved=True).count()
    total    = ErrorLog.objects.count()
    by_type  = (
        ErrorLog.objects
        .values('error_type')
        .order_by('error_type')
    )
    # Count per type manually (sqlite compatible)
    type_counts = {}
    for e in ErrorLog.objects.all():
        type_counts[e.error_type] = type_counts.get(e.error_type, 0) + 1

    return render(request, 'errors/error_list.html', {
        'errors': errors,
        'resolved_count': resolved,
        'total': total,
        'type_counts': sorted(type_counts.items(), key=lambda x: -x[1]),
    })


@role_required('admin', 'teacher')
def error_detail(request, pk):
    error = get_object_or_404(ErrorLog, pk=pk)
    return render(request, 'errors/error_detail.html', {'error': error})


@role_required('admin', 'teacher')
def error_resolve(request, pk):
    error = get_object_or_404(ErrorLog, pk=pk)
    error.resolved = True
    error.save()
    messages.success(request, f"Error #{pk} marked as resolved.")
    return redirect('error_list')


@role_required('admin', 'teacher')
def error_clear(request):
    if request.method == 'POST':
        count, _ = ErrorLog.objects.filter(resolved=True).delete()
        messages.success(request, f"Cleared {count} resolved error(s).")
    return redirect('error_list')
