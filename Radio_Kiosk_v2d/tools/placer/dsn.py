import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); print('fp',len(b.GetFootprints()),'tracks',len(list(b.Tracks())))
print('dsn',pcbnew.ExportSpecctraDSN(b,sys.argv[2]))
