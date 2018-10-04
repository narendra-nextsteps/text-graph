"""Add Assign task to the db."""
from graph_curation.db import db_nomenclature as _db_nomenclature
from graph_curation.db import db_objects as _db_objects


def assign_task_query(assigned_by, assigned_to_list, chapter_key):
    """Assign task to the user.

    Parameters
    ----------
    assigned_by : string
        by which user task is assigned
    assigned_to_list : list
        to which users or user task is assigned
    chapter_key : string
        which chapter is assigned

    Returns
    -------
    string
        Query for assigning a task to a user

    """
    return """
    LET assigned_by = "{assigned_by}"
    LET assigned_to_list = {assigned_to_list}
    LET chapter_key = "{chapter_key}"
    LET num_one_less_assigned_to = LENGTH(assigned_to_list) - 1

    LET chapter_doc = DOCUMENT(CONCAT("{chapter_collection}/", chapter_key))
    LET is_previously_locked = !IS_NULL(chapter_doc.locked_to)

    LET tasks = (
        FOR assigned_to_pos in 0..num_one_less_assigned_to
            FILTER assigned_to_list[assigned_to_pos] != chapter_doc.locked_to
            INSERT {{
                status: assigned_to_pos == 0 ? (
                    is_previously_locked ? 'NOT_YET_ASSIGNED' : 'PENDING'
                ) : 'NOT_YET_ASSIGNED',
                assigned_to: assigned_to_list[assigned_to_pos],
                assigned_by: assigned_by,
                chapter_key: chapter_key,
                chapter: chapter_doc.chapter,
                assigned_time: DATE_ISO8601(DATE_NOW())
            }} IN {task_collection}
            RETURN NEW
    )

    LET updated_chapter_doc = (
        FILTER IS_NULL(chapter_doc.locked_to)
        UPDATE chapter_doc WITH {{
            locked_to: assigned_to_list[0]
        }} IN {chapter_collection}
        RETURN NEW
    )

    LET need_to_create_subtasks = tasks[0].status == 'PENDING'

    LET mcqs = (
        FILTER need_to_create_subtasks
        FOR mcq in {mcqs_collection}
            FILTER chapter_doc.chapter_id == mcq.chapterId
            RETURN mcq
    )

    LET sub_tasks = (
        FILTER need_to_create_subtasks
        FOR mcq in mcqs
            INSERT {{
                task_key: tasks[0]._key,
                mcq_key: mcq._key,
                mcq_Id: mcq.mcqId,
                status: 'PENDING',
                assigned_time: DATE_ISO8601(DATE_NOW())
            }} IN {sub_task_collection}
            RETURN NEW
    )

    LET update_mcq = (
        FILTER need_to_create_subtasks
        FOR mcq in Mcqs
            UPDATE mcq with {{
                status: "PENDING"
            }} IN {mcqs_collection}
    )

    RETURN {{
        is_successful_execution: true
    }}
    """.format(
        assigned_by=assigned_by, assigned_to_list=assigned_to_list,
        chapter_key=chapter_key,
        sub_task_collection=_db_nomenclature.SUBTASK_COLLECTION,
        chapter_collection=_db_nomenclature.CHAPTER_COLLECTION,
        mcqs_collection=_db_nomenclature.MCQS_COLLECTION,
        task_collection=_db_nomenclature.TASK_COLLECTION
    )


def assign_task_query_response(
        assigned_by, assigned_to_list, chapter_key
):
    """Assign task query response.

    Parameters
    ----------
    assigned_by : string
        by which user task is assigned
    assigned_to_list : list
        by which users or user task is assigned
    chapter_key : string
        which chapter is assigned
    Returns
    -------
    api_output_pb2.Acknowledgement
        return valid execution true or flase

    """
    query_response = \
        _db_objects.graph_db().AQLQuery(
            assign_task_query(assigned_by, assigned_to_list, chapter_key)
        ).response
    if query_response['error'] or len(query_response['result']) is 0:
        return {"is_successful_execution": False}
    return query_response['result'][0]
