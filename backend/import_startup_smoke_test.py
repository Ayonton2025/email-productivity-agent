"""Import & startup smoke test for the project.
Run inside the backend Python environment.
"""
import sys

results = {}

try:
    import app.scripts.init_db as init_mod
    results['init_db_import'] = 'ok'
    results['init_mod_has_wait_for_db'] = hasattr(init_mod, 'wait_for_db')
    results['init_mod_has_is_already_initialized'] = hasattr(init_mod, 'is_already_initialized')
    results['init_mod_has_main'] = hasattr(init_mod, 'main')
except Exception as e:
    results['init_db_import'] = f'error: {type(e).__name__}: {e}'

try:
    import app.core.security as sec
    results['security_import'] = 'ok'
    results['security_has_get_current_user'] = hasattr(sec, 'get_current_user')
    results['security_dep_lazy'] = hasattr(sec, '_lazy_get_db')
except Exception as e:
    results['security_import'] = f'error: {type(e).__name__}: {e}'

try:
    import app.models.database as dbm
    results['database_import'] = 'ok'
    results['database_has_init_db'] = hasattr(dbm, 'init_db')
    results['database_has_get_db'] = hasattr(dbm, 'get_db')
    results['database_has_async_session'] = hasattr(dbm, 'AsyncSessionLocal')
except Exception as e:
    results['database_import'] = f'error: {type(e).__name__}: {e}'

try:
    import app.main as main_mod
    results['main_import'] = 'ok'
    results['main_has_app'] = hasattr(main_mod, 'app')
    results['main_startup_ready'] = getattr(main_mod, 'startup_ready', None)
except Exception as e:
    results['main_import'] = f'error: {type(e).__name__}: {e}'

print('\nSMOKE TEST RESULTS')
for k, v in results.items():
    print(f"{k}: {v}")

if results.get('database_import') == 'ok' and results.get('database_has_get_db'):
    print('\nDatabase.get_db is present and ready for dependency use')

print('\nSmoke test complete')
