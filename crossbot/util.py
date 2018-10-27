def comma_and(strings):
    # copy so we can get length and mutate
    strings = list(strings)
    n = len(strings)
    if n == 0:
        return ''
    if n == 1:
        return strings[0]
    if n == 2:
        return ' and '.join(strings)

    assert n > 2
    strings[-1] = 'and ' + strings[-1]
    return ', '.join(strings)
