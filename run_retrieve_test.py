from services import vector_memory_service as vms
print('calling retrieve_relevant_chunks')
try:
    cm, sm = vms.retrieve_relevant_chunks('What is this case about?', 6, max_results=8)
    print('context len', len(cm))
    print('sources', sm)
except Exception as e:
    import traceback
    traceback.print_exc()
    print('ERROR', e)
