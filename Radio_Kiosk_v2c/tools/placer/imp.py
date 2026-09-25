import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); pcbnew.ImportSpecctraSES(b,sys.argv[2]); pcbnew.SaveBoard(sys.argv[3],b)
print('fp',len(b.GetFootprints()),'tracks',len(list(b.Tracks())))
