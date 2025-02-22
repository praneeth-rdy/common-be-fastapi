import pybars

from app.server.utils import file_utils
from app.server.vendor.client import blob_service_client


async def get_template(file_path, **kwargs):
    template_string = await file_utils.read_file(file_path)
    compiler = pybars.Compiler()
    template = compiler.compile(str(template_string, 'utf-8'))
    kwargs['storage_account_name'] = blob_service_client.account_name
    return template(kwargs)
