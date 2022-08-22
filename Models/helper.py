# so ConversationHandler doesn't throw errors
MC_END_DATE, MC_URTI, MC_SUCCESS = range(3)
OFF_END_DATE, OFF_TYPE, OFF_SUCCESS = range(3)
RSLOCATION, RSTYPE = range(2)
REGISTERNAME, REGISTERFINISH = range(2)
LTREACHCLINIC, LTLEFTCLINIC, LTREACHHOUSE = range(3)
AWARD_OFF_NUMBER, AWARD_OFF_UPDATE = range(2)


# TODO: handle rank promotion
# Models functions
def append_dict(ref, key, value):
    _dict = ref.get()
    _dict[key] = value
    return ref.set(_dict)
