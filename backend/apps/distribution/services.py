from .models import DistributionStaffAssignment


def assign_default_distribution_staff(distribution, user):
    if distribution is None or user is None:
        return

    DistributionStaffAssignment.objects.get_or_create(
        distribution=distribution,
        user=user,
    )