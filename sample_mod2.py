from pyresttest import validators
val =  'contains' in validators.VALIDATORS
print 'Second module status of registered validator: {0}'.format(val)

def has_val():
    tested =  'contains' in validators.VALIDATORS
    print 'Second module status of registered validator: {0}'.format(tested)