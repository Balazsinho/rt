# -*- coding: utf-8 -*-


class Fields(object):
    """
    These Fields will be mapped to the usable fields to make the further
    processing easier. These are basically the internal representation of all
    the data that is coming from the documents. An example:

    "MT ugyfel-azonosito" and "MT ID" are both mapped to MT_ID constant,
    so after the processing they can easily be accessed using that single
    identifier.

    *** IMPORTANT ***
    If you add a new field, don't forget to add it to the USABLE_FIELDS,
    otherwise it won't appear in the final, filtered resultset
    """
    # ======================================================================
    # MIND
    # ======================================================================
    MT_ID = 'mt_id'
    ADDR1 = 'addr1'
    NAME1 = 'name1'
    NAME2 = 'name2'
    PHONE1 = 'phone1'
    PHONE2 = 'phone2'
    AGREED_TIME_FROM = 'agreed_time_from'
    AGREED_TIME_TO = 'agreed_time_to'
    AGREED_TIME_RAW = 'agreed_time_raw'
    REQ_TYPE = 'req_type'

    TITLE = 'title'
    REMARKS = 'remarks'

    DEVICES = 'devices'
    DEV_TYPE = 'device_type'
    DEV_SN = 'device_sn'
    DEV_OWNERSHIP = 'device_ownership'
    DEV_ACTION = 'device_action'
    DEV_CARD_SN = 'device_card_sn'

    EXTRA_DEVICES = 'extra_devices'
    EXTRA_DEV_TYPE = 'extra_dev_type'
    EXTRA_DEV_CODE = 'extra_dev_code'

    FLIP_ID = 'flip_id'

    # ======================================================================
    # MUNKALAP - RÉGI FORMÁTUM
    # ======================================================================

    EFP_NUM = 'efp_num'
    KI_ID = 'ki_id'
    TASK_TYPE = 'task_type'

    # ======================================================================
    # HIBALAP - ÚJ FORMÁTUM
    # ======================================================================
    A_NUM = 'a_num'
    SLA_H = 'sla_h'
    TICKET_ID = 'ticket_id'
    TASK_ID = 'task_id'
    CONTACT_NAME = 'contact_name'

    # ======================================================================
    # MUNKALAP - ÚJ FORMÁTUM
    # ======================================================================
    ORDER_NUM = 'order_num'
    OSS_ID = 'oss_id'
    DATE_CREATED = 'date_created'
    COLLECTABLE_MONEY = 'collectable_money'

    # ======================================================================
    # SZAMITOTT MEZOK
    # ======================================================================
    CITY = 'city'
    ZIP = 'zip'
    STREET = 'street'
    HOUSE_NUM = 'house_num'
    TASK_TYPE_LIST = 'task_type_list'
