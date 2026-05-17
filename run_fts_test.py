import database
print('calling search_chunks_fts')
try:
    res = database.search_chunks_fts('What is this case about?', 6)
    print('RESULT LENGTH', len(res))
    if res:
        print(res[0])
except Exception as e:
    import traceback
    traceback.print_exc()
    print('ERROR', e)
