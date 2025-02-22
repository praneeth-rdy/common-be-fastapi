def get_agg_projections(*args, include=True):
    projection = get_projections(*args, include)
    return {'$project': projection}


def get_projections(*args, include=True):
    return {arg: 1 if include else 0 for arg in args}
