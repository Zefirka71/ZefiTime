import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")


def before_scenario(context, scenario):
    from django.test.runner import DiscoverRunner
    context.runner = DiscoverRunner(verbosity=0)
    context.old_config = context.runner.setup_databases()


def after_scenario(context, scenario):
    context.runner.teardown_databases(context.old_config)
