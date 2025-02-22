import copy
from typing import Any, Optional, Union

from bson.objectid import ObjectId
from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorClientSession
from pymongo import UpdateOne
from pymongo.errors import DuplicateKeyError

from app.server.database.db import client, mongo
from app.server.models.core_data import CreateData
from app.server.utils import date_utils

# crud operations


def _prepare_update(update: dict[str, Any], timestamp: int) -> dict[str, Any]:
    """
    Prepare an update dictionary by adding a '$set' key if it doesn't exist,
    and updating the 'updated_at' field with the provided timestamp.

    Args:
        update (dict): The update dictionary.
        timestamp (int): The timestamp to update the 'updated_at' field with.

    Returns:
        dict: The modified update dictionary.
    """
    update.setdefault('$set', {})
    update['$set'].update({'updated_at': timestamp})
    return update


def _prepare_upsert(update: dict[str, Any], timestamp: int) -> dict[str, Any]:
    """
    Generate a dictionary update for upsert operations.

    Args:
        update (dict): The dictionary update.
        timestamp (str): The timestamp string.

    Returns:
        dict: The updated dictionary.
    """
    update.setdefault('$setOnInsert', {})
    update['$setOnInsert'].update({'_id': str(ObjectId()), 'created_at': timestamp})

    if 'is_deleted' not in update['$set']:
        update['$setOnInsert'].update({'is_deleted': False})

    return update


async def get_session() -> AsyncIOMotorClientSession:
    """
    Get a new session from the MongoDB client.

    Returns:
        AsyncIOMotorClientSession: The MongoDB client session.
    """
    return await client.start_session()


async def create_one(collection_name: str, data: dict[str, Any], options: dict[str, Any] = None, session: AsyncIOMotorClientSession = None) -> dict[str, Any]:
    """
    Insert one operation on the database.

    Args:
        collection_name (str): The name of the collection.
        data (dict): The document to be inserted.
        options (dict[str, Any]): A dictionary of fields with value 1 or 0. 1 - to select, 0 - de-select.
        session (AsyncIOMotorClientSession): The session to use for the insertion (default: None).

    Raises:
        HTTPException: If the document insertion fails.

    Returns:
        dict[str, Any]: The inserted document.
    """
    # Get the collection
    collection = mongo.get_collection(collection_name)

    # Parse and encode the data
    data = CreateData.model_validate(data)
    data = jsonable_encoder(data)

    # Try to insert the data into the collection
    model = None
    try:
        model = await collection.insert_one(data, session=session)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f'{collection_name}: + {error.details}') from error

    # Check if the insertion was successful
    if not model.inserted_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'{collection_name}: Failed to create')

    # If a session was provided, return the inserted document ID
    if session:
        return {'_id': model.inserted_id}

    # Fetch the inserted document from the collection
    model = await collection.find_one({'_id': model.inserted_id}, options)
    return model


async def create_one_time_series(collection_name: str, meta_data: dict[str, Any], body: dict[str, Any], session: AsyncIOMotorClientSession = None) -> dict[str, Any]:
    """
    Insert one operation on the database.

    Args:
        collection_name (str): The name of the collection.
        data (dict): The document to be inserted.
        options (dict[str, Any]): A dictionary of fields with value 1 or 0. 1 - to select, 0 - de-select.
        session (AsyncIOMotorClientSession): The session to use for the insertion (default: None).

    Raises:
        HTTPException: If the document insertion fails.

    Returns:
        dict[str, Any]: The inserted document.
    """
    # Get the collection
    collection = mongo.get_collection(collection_name)
    data = {'metadata': meta_data}
    data['body'] = body
    # Parse and encoe the data
    data = CreateData.model_validate(data)
    data = jsonable_encoder(data)
    data['timestamp'] = date_utils.get_current_timestamp_in_seconds()
    # Try to insert the data into the collection
    model = None
    model = await collection.insert_one(data, session=session)

    # Check if the insertion was successful
    if not model.inserted_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'{collection_name}: Failed to create')

    # If a session was provided, return the inserted document ID
    if session:
        return {'_id': model.inserted_id}

    # Fetch the inserted document from the collection
    model = await collection.find_one({'_id': model.inserted_id})
    return model


async def create_many(collection_name: str, data: list[dict[str, Any]], session: AsyncIOMotorClientSession = None) -> dict[str, Any]:
    """
    Insert multiple documents into a database collection.

    Args:
        collection_name (str): The name of the collection to insert into.
        data (list[dict[str, Any]]): The list of documents to be inserted.
        session (AsyncIOMotorClientSession, optional): The database session to use. Defaults to None.

    Raises:
        HTTPException: Raises an exception if document insertion fails.

    Returns:
        dict[str, Any]: A dictionary with the IDs of the inserted documents.
    """
    # Get the database collection
    collection = mongo.get_collection(collection_name)

    # Parse the data into a list of CreateData objects
    data = [CreateData.model_validate(indi_data) for indi_data in data]

    # Convert the data to JSON-serializable format
    data = jsonable_encoder(data)

    model = None
    try:
        # Insert the data into the collection
        model = await collection.insert_many(data, session=session)
    except Exception as error:
        # Raise an exception if the insertion fails
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'{collection_name}: + {str(error)}') from error

    if not model.inserted_ids:
        # Raise an exception if no documents were inserted
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'{collection_name}: Failed to create')

    return {'ids': model.inserted_ids}


async def read_one(collection_name: str, data_filter: Union[dict[str, Any], str], options: dict[str, Any] = None) -> dict[str, Any]:
    """
    Read One operation on database

    Args:
        collection_name (str): The name of the collection to read from
        data_filter (Union[dict[str, Any], str]): The filter to apply when querying the collection
        options (dict[str, Any]): A dictionary of fields with value 1 or 0. 1 - to select, 0 - de-select.

    Returns:
        dict[str, Any]: The document that matches the filter, or an empty dictionary if no document is found
    """
    # Get the collection
    collection = mongo.get_collection(collection_name)

    # Set options to None if not provided
    if not options:
        options = None

    # Find the document that matches the filter and return it, or an empty dictionary if not found
    model = await collection.find_one(data_filter, options)
    return model or {}


# pylint: disable=too-many-positional-arguments, too-many-arguments
async def read_many(
    collection_name: str, data_filter: dict[str, Any], options: dict[str, Any] = None, sort: dict[str, Any] = None, page: Optional[int] = None, page_size: Optional[int] = None
) -> list[dict[str, Any]]:
    """
    Retrieve multiple documents from a database collection.

    Args:
        collection_name (str): Name of the collection.
        data_filter (dict): Dictionary of fields to apply a filter for.
        options (dict[str, Any]): A dictionary of fields with value 1 or 0. 1 - to select, 0 - de-select.
        sort (dict): Dictionary of fields to specify the sorting order.
        page (int, optional): Page number for pagination. Defaults to None.
        page_size (int, optional): Number of documents per page for pagination. Defaults to None.

    Returns:
        list[dict[str, Any]]: List of retrieved documents.
    """
    collection = mongo.get_collection(collection_name)  # Get the collection object

    if not options:
        options = None

    # Retrieve the documents from the collection based on the filter and options
    models = collection.find(data_filter, options)

    if sort:
        sort_query = list(sort.items())
        models.sort(sort_query)  # Sort the retrieved documents based on the specified order

    if page and page > 0:
        offset = page_size if page_size and page_size > 0 else 0
        models.skip((page - 1) * offset)  # Apply pagination by skipping documents

    if page_size and page_size > 0:
        models.limit(page_size)  # Limit the number of documents per page

    return await models.to_list(None)  # Return the list of retrieved documents


# pylint: disable=too-many-positional-arguments,too-many-arguments
async def update_one(
    collection_name: str,
    record_id: str = None,
    data_filter: dict[str, Any] = None,
    update: dict[str, Any] = None,
    options: dict[str, Any] = None,
    upsert: bool = False,
    session: AsyncIOMotorClientSession = None,
) -> dict[str, Any]:
    """Find one and update operation on the database.

    Args:
        collection_name (str): The name of the collection.
        record_id (str): The ID of the document.
        data_filter (dict[str, Any]): A dictionary of fields to apply a filter for.
        update (dict[str, Any]): A dictionary of field data to be updated.
        options (dict[str, Any]): A dictionary of fields with value 1 or 0. 1 - to select, 0 - de-select.
        upsert (bool): Whether to perform an upsert operation.
        session (AsyncIOMotorClientSession): The MongoDB session.

    Raises:
        HTTPException: Raised if the filter dict is not set.
        HTTPException: Raised if the update dict is not set.
        HTTPException: Raised if the update fails.

    Returns:
        dict[str, Any]: The updated document.
    """
    collection = mongo.get_collection(collection_name)

    # If record_id is provided, set it as the filter
    if record_id:
        data_filter = {'_id': record_id}

    # Check if data_filter is empty
    if not data_filter:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'{collection_name}: filter params cannot be empty')

    # Check if update is empty
    if not update:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'{collection_name}: update params cannot be empty')

    # Get the current timestamp
    timestamp = date_utils.get_current_timestamp()

    # Prepare the update data
    update_data = copy.deepcopy(update)
    update_data = _prepare_update(update_data, timestamp)

    # If upsert is True, prepare the data for upsert operation
    if upsert:
        update_data = _prepare_upsert(update_data, timestamp)

    # If options is empty, set it to None
    if not options:
        options = None

    try:
        # Find one document and perform the update
        model = await collection.find_one_and_update(data_filter, update_data, options, upsert=upsert, return_document=True, session=session)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f'{collection_name}: {error.details}') from error

    # If model is None, raise an exception
    if not model:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'{collection_name}: Failed to update')

    return model


async def update_many(collection_name: str, data_filter: dict[str, Any], update: dict[str, Any], upsert: bool = False, session: AsyncIOMotorClientSession = None) -> dict[str, Any]:
    """Update multiple documents in a collection.

    Args:
        collection_name (str): The name of the collection.
        data_filter (dict[str, Any]): The filter to apply for the update operation.
        update (dict[str, Any]): The data to be updated in the documents.

    Raises:
        HTTPException: Raised if either data_filter or update is empty.

    Returns:
        dict[str, Any]: A dictionary with the modified_count field.
    """
    if not data_filter or not update:
        empty_param = 'update' if data_filter else 'data_filter'
        raise HTTPException(422, f'{collection_name}: {empty_param} param cannot be empty')

    collection = mongo.get_collection(collection_name)
    timestamp = date_utils.get_current_timestamp()

    # Prepare update fields
    update = _prepare_update(update, timestamp)

    if upsert:
        # Prepare upsert fields
        update = _prepare_upsert(update, timestamp)

    try:
        model = await collection.update_many(data_filter, update, upsert=upsert, session=session)
    except Exception as error:
        raise HTTPException(422, f'{collection_name}: Failed to update') from error

    return {'modified_count': model.modified_count}


async def delete_one(collection_name: str, record_id: str = None, data_filter: dict[str, Any] = None, session: AsyncIOMotorClientSession = None) -> dict[str, Any]:
    """Delete a single document from a collection.

    Args:
        collection_name (str): The name of the collection.
        record_id (str): The ID of the document to delete.
        data_filter (dict[str, Any]): The filter criteria to find the document to delete.
        session (AsyncIOMotorClientSession): The session to use for the operation.

    Raises:
        HTTPException: Raised if the filter criteria is not set or is empty.
        HTTPException: Raised if the deletion fails.

    Returns:
        dict[str, Any]: The deleted document.
    """
    # Get the collection
    collection = mongo.get_collection(collection_name)

    # If record_id is provided, set data_filter to find the document with that ID
    if record_id:
        data_filter = {'_id': record_id}

    # If data_filter is not set, raise an exception
    if not data_filter:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'{collection_name}: filter params cannot be empty')

    # Find and delete the document using the data_filter and session
    model = await collection.find_one_and_delete(data_filter, session=session)

    # If no document was found, raise an exception
    if not model:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'{collection_name}: Failed to delete')

    return model


async def delete_many(collection_name: str, data_filter: dict[str, Any], session: AsyncIOMotorClientSession = None) -> dict[str, Any]:
    """
    Delete many documents from a collection in the database.

    Args:
        collection_name (str): The name of the collection to delete from.
        data_filter (dict): The filter to apply when deleting documents.
        session (AsyncIOMotorClientSession, optional): The session to use for the operation.
            Defaults to None.

    Raises:
        HTTPException: Raised if the filter is not set.
        HTTPException: Raised if the deletion fails.

    Returns:
        dict[str, Any]: A dictionary with the number of documents deleted.
    """
    # Get the collection from the database
    collection = mongo.get_collection(collection_name)

    # Raise an exception if the filter is empty
    if not data_filter:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'{collection_name}: filter cannot be empty')

    # Perform the delete many operation
    model = await collection.delete_many(data_filter, session=session)

    # Return the result
    return {'deleted_count': model.deleted_count}


async def count(collection_name: str, data_filter: dict[str, Any], session: AsyncIOMotorClientSession = None) -> dict[str, Any]:
    """
    Count the number of documents in a collection that match the given filter.

    Args:
        collection_name (str): The name of the collection to count documents from.
        data_filter (dict[str, Any]): A dictionary of fields to apply filter for.
        session (AsyncIOMotorClientSession, optional): The session to use for the operation. Defaults to None.

    Returns:
        dict[str, Any]: A dictionary with the count of documents.
    """
    collection = mongo.get_collection(collection_name)

    doc_count = await collection.count_documents(data_filter, session=session)
    return {'count': doc_count}


async def query_read(collection_name: str, aggregate: list[dict[str, Any]], page: Optional[int] = None, page_size: Optional[int] = None, paging_data: bool = False):
    """
    Read documents from a collection with optional pagination.

    Args:
        collection_name (str): The name of the collection.
        aggregate (list[dict[str, Any]]): The aggregation pipeline to apply.
        page (int, optional): The page number for pagination. Defaults to None.
        page_size (int, optional): The number of documents per page for pagination. Defaults to None.
        paging_data (bool, optional): Whether to include pagination metadata in the result. Defaults to False.

    Returns:
        dict: The result of the query, including the documents and optional pagination metadata.
    """
    # Get the collection
    collection = mongo.get_collection(collection_name)

    # Set default page size to 10 and limit it to 100
    page_size = min(page_size, 100) if page_size else 10

    # Set default page to 1 if not provided
    page = page or 1

    # Calculate the number of documents to skip based on page and page size
    skip = (page - 1) * page_size

    # If no aggregation pipeline is provided, set it to an empty list
    if not aggregate:
        aggregate = []

    # If paging_data is True, add pagination metadata
    if paging_data:
        aggregate += [
            {'$facet': {'data': [{'$skip': skip}, {'$limit': page_size + 1}], 'total_count': [{'$count': 'total'}]}},
            {
                '$addFields': {
                    'metadata': {
                        'current_page': page,
                        'page_size': page_size,
                        'total_records': {'$ifNull': [{'$arrayElemAt': ['$total_count.total', 0]}, 0]},
                        'has_next_page': {'$gt': [{'$size': '$data'}, page_size]},
                    }
                }
            },
            {'$project': {'data': {'$slice': ['$data', page_size]}, 'metadata': 1}},
        ]

        # Execute the aggregation pipeline and return the result
        result = await collection.aggregate(aggregate).to_list(None)
        return result[0]

    # If paging_data is False, perform simple aggregation and return the result
    aggregate += [{'$skip': skip}, {'$limit': page_size}]

    return await collection.aggregate(aggregate).to_list(None)


async def query_read_all(collection_name: str, aggregate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Query the specified collection with the given aggregation pipeline and return the results as a list.

    Args:
        collection_name (str): The name of the collection to query.
        aggregate (List[dict[str, Any]]): The aggregation pipeline to apply to the collection.

    Returns:
        list[dict[str, Any]]: The results of the aggregation as a list of dictionaries.
    """
    collection = mongo.get_collection(collection_name)
    if not aggregate:
        aggregate = []

    return await collection.aggregate(aggregate).to_list(None)


async def distinct(collection_name: str, field: str, data_filter: dict[str, Any] = None, session: AsyncIOMotorClientSession = None) -> dict[str, Any]:
    """
    Get distinct values for a field in a collection.

    Args:
        collection_name (str): The name of the collection.
        field (str): The field to get distinct values for.
        data_filter (dict[str, Any], optional): The filter to apply when querying the collection. Defaults to None.
        session (AsyncIOMotorClientSession, optional): The session to use for the operation. Defaults to None.
    Returns:
        dict[str, Any]: A dictionary containing the distinct values for the field.
    """
    # Get the collection
    collection = mongo.get_collection(collection_name)

    # Get distinct values for the field
    return await collection.distinct(field, data_filter, session)


def update_query(record_id: str = None, data_filter: dict[str, Any] = None, update: dict[str, Any] = None, upsert: bool = False) -> UpdateOne:
    """
    Constructs an UpdateOne object to update a record in MongoDB.

    Args:
        record_id (str, optional): The ID of the record to update. Defaults to None.
        data_filter (dict[str, Any], optional): The filter parameters to find the record. Defaults to None.
        update (dict[str, Any], optional): The update parameters to modify the record. Defaults to None.
        upsert (bool, optional): Whether to insert the document if it doesn't exist. Defaults to False.

    Raises:
        HTTPException: If the filter parameters or update parameters are empty.

    Returns:
        UpdateOne: The UpdateOne object to perform the update operation.
    """
    timestamp = date_utils.get_current_timestamp()

    if record_id:
        data_filter = {'_id': record_id}

    if not data_filter:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='filter params cannot be empty')

    if not update:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='update params cannot be empty')

    update_data = copy.deepcopy(update)
    update_data = _prepare_update(update_data, timestamp)

    if upsert:
        update_data = _prepare_upsert(update_data, timestamp)

    return UpdateOne(filter=data_filter, update=update_data, upsert=upsert)


async def bulk_write(collection_name: str, operations: list[Any], session: AsyncIOMotorClientSession = None) -> list[dict[str, Any]]:
    """
    Async function to perform bulk write operations on a collection.

    Args:
        collection_name (str): The name of the collection to perform the operations on.
        operations (list[Any]): List of operations to perform.

    Returns:
        list[dict[str, Any]]: List of results from the bulk write operations.
    """

    # Get the collection object from the MongoDB connection
    collection = mongo.get_collection(collection_name)

    # Perform the bulk write operations on the collection
    return await collection.bulk_write(operations, session=session)
