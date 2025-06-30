import os, glob
import csv
import pandas as pd
from collections import Counter
from datetime import datetime, timedelta
import auxfuncs as aux
import aixfuncs as af

def saveInferenceResult2CSV(infdata, infpath, bPrintOut=True):
    infdata.sort(key=lambda x: x['wsifname'], reverse=True)
    tsnow = datetime.now().strftime('%Y%m%d_%H%M%S')
    whichmodel, modelversion = infdata[0]['modelname'], infdata[0]['modelversion']
    outcsv = os.path.join(infpath, f'{whichmodel}_{modelversion}_inference_{tsnow}.csv')
    aux.printmsg(f'[INFO] Saving inference result to {os.path.basename(outcsv)}...', 'INFO')
    ##
    colMODEL = ['modelname', 'modelversion', 'similarity']
    colWSI = ['layer#', 'bestz', 'mpp', 'icc', 'width', 'height', 'medfsize(MB)', 'wsifsize(MB)']
    colENV = ['analysis_date', 'analysis_time', 'envOS', 'envCPU', 'envGPU', 'envRAM', 'scanner']
    with open(outcsv, 'w', newline='') as csvobj:
        if whichmodel == 'AIxURO':
            colCELLs = ['wsifname', 'suspicious', 'atypical', 'benign', 'degenerated', 'top24AVGncratio', 'top24AVGnucarea', 'scellAVGncratio', 'scellAVGnucarea', 'acellAVGncratio', 'acellAVGnucarea']
        else:   ## AIxTHY
            if modelversion[:6] in ['2025.2']:
                colCELLs = ['wsifname', 'follicular', 'oncocytic', 'epithelioid', 'lymphocytes', 'histiocytes', 'colloid']
            else:
                colCELLs = ['wsifname', 'follicular', 'hurthle', 'histiocytes', 'lymphocytes', 'colloid']
        fieldcols = colCELLs + colMODEL + colWSI + colENV
        csvwriter = csv.DictWriter(csvobj, fieldnames=fieldcols)
        csvwriter.writeheader()
        for ii in range(len(infdata)):
            thisrow = {}
            ## colCELLs
            thisrow['wsifname'] = infdata[ii]['wsifname']
            if whichmodel == 'AIxURO':
                thisrow['suspicious']      = infdata[ii]['cellCount'][2]
                thisrow['atypical']        = infdata[ii]['cellCount'][3]
                thisrow['benign']          = infdata[ii]['cellCount'][4]
                thisrow['degenerated']     = infdata[ii]['cellCount'][7]
                thisrow['top24AVGncratio'] = infdata[ii]['avgtop24ncratio']
                thisrow['top24AVGnucarea'] = infdata[ii]['avgtop24nucarea']
                thisrow['scellAVGncratio'] = infdata[ii]['savgncratio']
                thisrow['scellAVGnucarea'] = infdata[ii]['savgnucarea']
                thisrow['acellAVGncratio'] = infdata[ii]['aavgncratio']
                thisrow['acellAVGnucarea'] = infdata[ii]['aavgnucarea']
            else:   ## AIxTHY
                if modelversion[:6] in ['2025.2']:
                    thisrow['follicular']  = infdata[ii]['cellCount'][1]
                    thisrow['oncocytic']   = infdata[ii]['cellCount'][2]
                    thisrow['epithelioid'] = infdata[ii]['cellCount'][3]
                    thisrow['lymphocytes'] = infdata[ii]['cellCount'][4]
                    thisrow['histiocytes'] = infdata[ii]['cellCount'][5]
                    thisrow['colloid']     = infdata[ii]['cellCount'][6]
                else:
                    thisrow['colloid']     = infdata[ii]['cellCount'][5]
                    thisrow['hurthle']     = infdata[ii]['cellCount'][2]
                    thisrow['histiocytes'] = infdata[ii]['cellCount'][3]
                    thisrow['lymphocytes'] = infdata[ii]['cellCount'][4]
                    thisrow['follicular']  = infdata[ii]['cellCount'][1]
            ## colMODEL = ['modelname', 'modelversion', 'similarity']
            thisrow['modelname'] = infdata[ii]['modelname']
            thisrow['modelversion'] = infdata[ii]['modelversion']
            thisrow['similarity'] = infdata[ii]['similarity']
            ## colWSI = ['layer#', 'bestz', 'mpp', 'icc', 'width', 'height', 'medfsize', 'wsifsize']
            thisrow['layer#'] = infdata[ii]['sizez']
            thisrow['bestz'] = infdata[ii]['bestfocusayer']
            thisrow['mpp'] = infdata[ii]['mpp']
            thisrow['icc'] = infdata[ii]['icc']
            thisrow['width'] = infdata[ii]['width']
            thisrow['height'] = infdata[ii]['height']
            thisrow['medfsize(MB)'] = infdata[ii]['medfsize']
            thisrow['wsifsize(MB)'] = infdata[ii]['wsifsize']
            ## colENV = ['analysis_date', 'analysis_time', 'envOS', 'envCPU', 'envGPU', 'envRAM', 'scanner']
            thisrow['analysis_date'] = datetime.fromtimestamp(infdata[ii]['execution_date']).strftime('%Y-%m-%d %H:%M:%S')
            tsstr = (datetime.min+timedelta(seconds=infdata[ii]['analysis_timestamp'])).strftime('%H:%M:%S')[:-3]
            thisrow['analysis_time'] = tsstr
            thisrow['envOS'], thisrow['envCPU'], thisrow['envGPU'], thisrow['envRAM'] = aux.getConfigHWcomponents()
            thisrow['scanner'] = infdata[ii]['scanner']
            csvwriter.writerow(thisrow)
    aux.printmsg(f'[INFO] Inference result saved to {os.path.basename(outcsv)} completed.', 'INFO')
    if bPrintOut:
        aux.printdata('-'*240)
        toprow = f"{'wsi filename':<32}"
        if whichmodel == 'AIxURO':
            toprow += f"{'suspicious':<12}{'atypical':<12}{'benign':<12}{'degenerated':<12}"
        else:   ## AIxTHY
            if modelversion[:6] in ['2025.2']:
                toprow += f"{'follicular':<12}{'oncocytic':<12}{'epithelioid':<12}{'lymphocytes':<12}{'histiocytes':<12}{'colloid':<12}"
            else:
                toprow += f"{'follicular':<12}{'hurthle':<12}{'lymphocytes':<12}{'histiocytes':<12}{'colloid':<12}"
        toprow += f"{'width':>8,}{'height':>8,}{'model name&ver':^20}{'similarity':^10,.4f}{'analysis time':^14}"
        aux.printdata(toprow)
        aux.printdata('-'*240)
        for ii in range(len(infdata)):
            d = infdata[ii]
            thisrow = f"{d['wsifname'][:30]:<32}"
            if whichmodel == 'AIxURO':
                thisrow += f"{d['cellCount'][2]:>12,}{d['cellCount'][3]:>12,}{d['cellCount'][4]:>12,}{d['cellCount'][7]:>12,}"
            else:   ## AIxTHY
                if modelversion[:6] in ['2025.2']:
                    thisrow += f"{d['cellCount'][1]:>12,}{d['cellCount'][2]:>12,}{d['cellCount'][3]:>12,}{d['cellCount'][4]:>12,}{d['cellCount'][5]:>12,}{d['cellCount'][6]:>12,}"
                else:
                    thisrow += f"{d['cellCount'][1]:>12,}{d['cellCount'][2]:>12,}{d['cellCount'][4]:>12,}{d['cellCount'][3]:>12,}{d['cellCount'][5]:>12,}"
            thismodel = d['modelname']+' '+d['modelversion']
            tsstr = (datetime.min+timedelta(seconds=infdata[ii]['analysis_timestamp'])).strftime('%H:%M:%S')[:-3]
            thisrow += f"{d['width']:>8,}{d['height']:>8,}{thismodel:^20}{d['similarity']:^10.4f}{tsstr:>14}"
            aux.printdata(thisrow)
        aux.printdata('-'*240)

def saveAIXmetadata2CSV(csvfname, modelname, aixdata):
    print(f'{aux.sNOW()}[INFO] Saving AIX metadata into {os.path.basename(csvfname)}...')
    with open(csvfname, 'w', newline='') as csvobj:
        if modelname == 'AIxURO':
            headcols = ['cellname', 'category', 'score', 'sizez', 'layer#', 'bestz', 'cellarea', 'ncratio', 'tilex', 'tiley', 'tilew', 'tileh']
        else:
            headcols = ['cellname', 'category', 'score', 'sizez', 'layer#', 'bestz', 'cellarea', 'tilex', 'tiley', 'tilew', 'tileh']
        tagscols = [f'trait_{ii+1}' for ii in range(len(aixdata[i]['traits']))]
        fieldcol = headcols + tagscols
        csvwriter = csv.DictWriter(csvobj, fieldnames=fieldcol)
        csvwriter.writeheader()
        for i in range(len(aixdata)):
            thisrow = {}
            thisrow['cellname'] = aixdata[i]['cellname']
            thisrow['category'] = aixdata[i]['category']
            thisrow['score'] = aixdata[i]['score']
            thisrow['sizez'] = aixdata[i]['sizez']
            thisrow['layer#'] = aixdata[i]['layer#']
            thisrow['bestz'] = aixdata[i]['bestz']
            thisrow['cellarea'] = aixdata[i]['cellarea']
            if modelname == 'AIxURO':
                thisrow['ncratio'] = aixdata[i]['ncratio']
            thisrow['tilex'], thisrow['tiley'], thisrow['tilew'], thisrow['tileh'] = aixdata[i]['tilex'], aixdata[i]['tiley'], aixdata[i]['tilew'], aixdata[i]['tileh']
            for ii in range(len(aixdata[i]['traits'])):
                thisrow[f'trait_{ii+1}'] = aixdata[i]['traits'][ii]
            csvwriter.writerow(thisrow)
    print(f'{aux.sNOW()}[INFO] metadata saved to {os.path.basename(csvfname)} completed.')

## retrieve metadata from multiple layers of .aix files, summarize them into a csv file
## need mpp data to calculate the cell area
def processAIXmetadata(aixpath, bestZ, mpp=0.25):
    if not os.path.isdir(aixpath):
        print(f'{aux.sNOW()}[ERROR] {aixpath} is not a directory.')
        return
    aixlist = glob.glob(os.path.join(aixpath, '*.aix'))
    aixlist.sort()
    nlayers = len(aixlist)
    if nlayers == 0:
        print(f'{aux.sNOW()}[ERROR] No .aix files found in {aixpath}.')
        return
    ## preparation
    csvpath = f'{os.path.dirname(aixlist[0])}\\csvfiles'
    if os.path.isdir(csvpath) == False:
        os.mkdir(csvpath)    
    ## retrieve metadata from aix file, and save them into a csv file
    print(f'{aux.sNOW()}[INFO] Processing {os.path.basename(aixpath)}...')
    for ii in range(nlayers):
        aixfile = aixlist[ii]
        aixinfo, cellCount, tclist = af.getCellsInfoFromAIX(aixfile)
        #tclist = sorted(allCells, key=lambda x: (-x['category'], x['score']), reverse=True)
        thismodel = aixinfo['Model']
        thisversion = aixinfo['ModelVersion']
        ## Categories
        if (thismodel == 'AIxURO'):
            ## 1: nuclei, 2: suspicious, 3: atypical, 4: benign, 5: other,
            ## 6: tissue, 7: degenerated
            tcCategories = [2, 3, 4, 5, 6, 7]
        elif (thismodel == 'AIxTHY'):
            ## model: 2024.2-0625
            ## 1: Follicular, 2: Hurthle, 3: Histiocytes, 4: Lymphocytes, 
            ## 5: Colloid, 6: Multinucleated giant cells
            ## model: 2025.2-0526
            ## 1: Follicular, 2: Oncocytic, 3: Epithelioid, 4: Lymphocytes/Lymphoid, 
            ## 5: Histiocytes, 6: Colloid
            tcCategories = [1, 2, 3, 4, 5, 6]
        else:
            print(f'{aux.sNOW()}[ERROR] {aixpath} is not an AIxURO or AIxTHY model.')
            return
        aixMetadata = []
        for jj in range(len(tclist)):
            if (tclist[jj]['category'] not in tcCategories):
                continue
            thisdata = {}
            thisdata['cellname'] = tclist[jj]['cellname']
            thisdata['category'] = af.getCategoryName(thismodel, thisversion, tclist[jj]['category'])
            thisdata['score'] = tclist[jj]['score']
            thisdata['tilex'], thisdata['tiley'], thisdata['tilew'], thisdata['tileh'] = aux.getCellTilePos(tclist[jj]['segments'])
            thisdata['layer#'], thisdata['sizez'], thisdata['bestz'] = ii+1, nlayers, bestZ
            if aixinfo['Model'] == 'AIxURO':
                #thisdata['score'] = tclist[jj]['score']
                #thisdata['probability'] = tclist[jj]['probability']
                thisdata['cellarea'] = aux.calculateCellArea(tclist[jj]['segments'], mpp)
                thisdata['ncratio'] = tclist[jj]['ncratio']
            thisdata['traits'] = tclist[jj]['traits']
            aixMetadata.append(thisdata)
        ## save metadata into a csv file
        csvfile = os.path.join(csvpath, f'{os.path.splitext(os.path.basename(aixfile))[0]}.csv')
        saveAIXmetadata2CSV(csvfile, aixinfo['Model'], aixMetadata)
        ##
        print(f'{aux.sNOW()}[INFO] {os.path.basename(aixfile)} layer-{ii+1}: {cellCount}')
    print(f'{aux.sNOW()}[INFO] processAIXmetadata({aixpath}) completed')

## process data by Pandas
def chooseKeepRecord(fidx, layers, bestz):
    cidx = [abs(layers[fidx[i]]-bestz) for i in range(len(fidx))]
    minii = min(cidx)
    whichone = cidx.index(minii)
    #print(f'{[layers[fidx[i]] for i in range(len(fidx))]}-{cidx}\t{minii}')
    return whichone

def OLD_removeDuplicateCountedCells(sortedcsv):
    neatcsv = f'{os.path.splitext(sortedcsv)[0][:-6]}neat.csv'
    ## load cell tile (x, y, w, h)
    dfsorted = pd.read_csv(sortedcsv)
    cx = dfsorted['tilex'].tolist()
    cy = dfsorted['tiley'].to_list()
    cw = dfsorted['tilew'].tolist()
    ch = dfsorted['tileh'].to_list()
    cz = dfsorted['layer#'].tolist()
    #
    idx = 0
    found_s, found_e = 0, 0
    foundlist = []
    while idx < len(cx):
        if (idx+1) >= len(cx):
            break
        x1, y1, w1, h1 = cx[idx], cy[idx], cw[idx], ch[idx]
        x2, y2, w2, h2 = cx[idx+1], cy[idx+1], cw[idx+1], ch[idx+1]
        overlap_ratio, intersected_area = aux.getIntersectionArea(x1, y1, w1, h1, x2, y2, w2, h2)
        #
        found_s = idx
        isFound = False
        while overlap_ratio > 0.85:
            isFound = True
            found_e = idx+1
            if found_e >= len(cx) or found_e+1 >= len(cx):
                break
            x1, y1, w1, h1 = cx[found_e], cy[found_e], cw[found_e], ch[found_e]
            x2, y2, w2, h2 = cx[found_e+1], cy[found_e+1], cw[found_e+1], ch[found_e+1]
            overlap_ratio, _ = aux.getIntersectionArea(x1, y1, w1, h1, x2, y2, w2, h2)
            idx += 1
        if isFound:
            thisfound = [i for i in range(found_s, found_e+1)]
            foundlist.append(thisfound)
        idx += 1
    ## remove same cells
    numDel = 0
    keeplist = []
    bestz = dfsorted['bestz'].values[0]
    for i in range(len(foundlist)):
        keepidx = chooseKeepRecord(foundlist[i], cz, bestz)
        keeplist.append(foundlist[i][keepidx])
        numDel += len(foundlist[i])-1
        for j in range(len(foundlist[i])):
            if j != keepidx:
                dfsorted.drop(foundlist[i][j], inplace=True, errors='ignore')
    print(f'{aux.sNOW()}[INFO] remove {numDel} rows')
    dfsorted.to_csv(neatcsv, index=False)
    return dfsorted, foundlist, keeplist

def removeDuplicateCountedCells(sortedcsv):
    neatcsv = f'{os.path.splitext(sortedcsv)[0][:-6]}neat.csv'
    ## load cell tile (x, y, w, h)
    dfsorted = pd.read_csv(sortedcsv)
    cx = dfsorted['tilex'].tolist()
    cy = dfsorted['tiley'].to_list()
    cw = dfsorted['tilew'].tolist()
    ch = dfsorted['tileh'].to_list()
    cz = dfsorted['layer#'].tolist()
    # search range
    searchRange = 2*dfsorted['sizez'].values[0]
    #
    nEntries = len(cx)
    ii, ci, ni = 0, 1, 1
    foundlist = []
    while ii < nEntries:
        #if (ci+1) >= nEntries:     ## last one
        #    break
        x1, y1, w1, h1 = cx[ii], cy[ii], cw[ii], ch[ii]
        #x2, y2 = x1, y1
        thisfound = [ii]
        found_duplicate = False
        #print(f'[debug] index: {ii}; current: {ci}; next: {ni}; (x,y): {cx[ii], cy[ii]}')
        #while y2-y1 < 50 and x2-x1 < 50:
        ni = 0      ## refreah ni
        for jj in range(searchRange):
            if ci+jj >= nEntries:
                ni = nEntries
                break
            x2, y2, w2, h2 = cx[ci+jj], cy[ci+jj], cw[ci+jj], ch[ci+jj]
            if abs(x2-x1) > 50:
                if ni == 0:
                    ni = ci+jj
                continue
            overlap_ratio, _ = aux.getIntersectionArea(x1, y1, w1, h1, x2, y2, w2, h2)
            if overlap_ratio > 0.85:
                thisfound.append(ci+jj)
                found_duplicate = True
            else:
                if ni == 0:
                    ni = ci+jj
        
        if found_duplicate:
            foundlist.append(thisfound)
        if ni+1 > nEntries:
            break
        else:
            ii, ci = ni, ni+1
    ## remove same cells
    numDel = 0
    keeplist = []
    bestz = dfsorted['bestz'].values[0]
    for i in range(len(foundlist)):
        keepidx = chooseKeepRecord(foundlist[i], cz, bestz)
        keeplist.append(foundlist[i][keepidx])
        numDel += len(foundlist[i])-1
        for j in range(len(foundlist[i])):
            if j != keepidx:
                dfsorted.drop(foundlist[i][j], inplace=True, errors='ignore')
    print(f'{aux.sNOW()}[INFO] remove {numDel} rows')
    dfsorted.to_csv(neatcsv, index=False)
    return dfsorted, foundlist, keeplist

def analyzeCellsCoverage(csvpath, sizez=1, steps=1):
    csvlist = glob.glob(os.path.join(csvpath, '*.csv'))
    csvlist.sort()
    ## number of layers for data analysis
    nlayers = len(csvlist)
    if (sizez & 1 == 0) or (nlayers & 1 == 0):  ## even layers
        print(f'{aux.sNOW()}[WARNING] can not analyze metadata from even number of layers')
        return
    elif sizez*steps > nlayers:
        print(f'{aux.sNOW()}[ERROR] lack of layers for analysis, total: {nlayers}; requested: {sizez}')
        return
    sidx = 0 if sizez == 1 else (nlayers//2)-((sizez//2)*steps)
    ## pandas load csv files
    dfz = []
    for i in range(sidx, nlayers, steps):
        thisdf = pd.read_csv(csvlist[i])
        dfz.append(thisdf)
    ## coverage anaysis
    dstpath = os.path.join(os.path.split(csvpath)[0], 'results')
    if os.path.isdir(dstpath) == False:
        os.mkdir(dstpath)
    dfallz = pd.concat([dfz[i] for i in range(len(dfz))])
    dfsortedallz = dfallz.sort_values(by=['tiley', 'tilex', 'tilew', 'tileh'], ascending=[True, True, False, False])
    sorted_csvfile = os.path.join(dstpath, f'{len(dfz)}L{steps}s_sorted.csv')
    dfsortedallz.to_csv(sorted_csvfile, index=False)
    ## remove duplicate count on same cell in multiple layers
    dfneat, samelist, keeplist = removeDuplicateCountedCells(sorted_csvfile)
    ## coverage distribution
    bestz = dfneat['bestz'].values[0]
    cellsCount = Counter(dfneat['layer#'])
    print(f'{aux.sNOW()}[INFO] total found cells in {len(dfz)}L{steps}s is {sum(cellsCount.values())}; found in bestz is {cellsCount[bestz]}')

## get cell inforation for compaing 
def getCellListInMultiLayers(csvfname, whichtype, whichlayer):
    if os.path.isfile(csvfname) == False:
        aux.printmsg(f'[ERROR] {csvfname} does not exist')
        return []
    
    dfcell = pd.read_csv(csvfname)
    thisdf = dfcell[dfcell['layer#'] == whichlayer]
    ## find the number of cells which category is whichtype
    candidx = thisdf.index[thisdf['category'] == whichtype].tolist()
    if len(candidx) == 0:
        aux.printmsg(f'[WARNING] no {whichtype} cells in layer-{whichlayer} of {os.path.splitext(os.path.basename(csvfname))[0]}')
        return []
    celllist = []
    for i in range(len(candidx)):
        celllist.append(dfcell.iloc[candidx[i]]['cellname'])
    return celllist

def getCellTilePosition(csvfname, cellname):
    tx, ty, tw, th = 0, 0, 0, 0
    if os.path.isfile(csvfname) == False:
        aux.printmsg(f'[ERROR] {csvfname} does not exist')
    else:
        dfcell = pd.read_csv(csvfname)
        tclist = dfcell.index[dfcell['cellname'] == cellname].tolist()
        if len(tclist) == 0:    ## 
            aux.printmsg(f'[ERROR] no cellname {cellname} in {os.path.basename(csvfname)}')
        elif len(tclist) > 1:
            aux.printmsg(f'[ERROR] there are {len(tclist)} cells named {cellname} in {os.path.basename(csvfname)}')
        else:
            tx = dfcell.iloc[tclist[0]]['tilex']
            ty = dfcell.iloc[tclist[0]]['tiley']
            tw = dfcell.iloc[tclist[0]]['tilew']
            th = dfcell.iloc[tclist[0]]['tileh']
    return tx, ty, tw, th

def getCellCategoriesAndTraits(csvfname, cellname):
    if os.path.isfile(csvfname) == False:
        aux.printmsg(f'[ERROR] {csvfname} does not exist')
        return [], []

    dfcell = pd.read_csv(csvfname)
    tclist = dfcell.index[dfcell['cellname'] == cellname].tolist()
    if len(tclist) == 0:    ## 
        aux.printmsg(f'[ERROR] no cellname {cellname} in {os.path.basename(csvfname)}')
    elif len(tclist) > 1:
        aux.printmsg(f'[ERROR] there are {len(tclist)} cells named {cellname} in {os.path.basename(csvfname)}')
    else:
        nlayers = dfcell.iloc[tclist[0]]['sizez']
        celltype = [f'z{i+1:02}' for i in range(nlayers)]
        nilscore = [0.0 for j in range(14)]     ## 14 is a magic number, which is max of tags
        tagscore = [nilscore for i in range(nlayers)]
        tx = dfcell.iloc[tclist[0]]['tilex']
        ty = dfcell.iloc[tclist[0]]['tiley']
        tw = dfcell.iloc[tclist[0]]['tilew']
        th = dfcell.iloc[tclist[0]]['tileh']
        ## find category and tags score in each layers
        cx, cy = dfcell['tilex'].tolist(), dfcell['tiley'].tolist()
        cw, ch = dfcell['tilew'].tolist(), dfcell['tileh'].tolist()
        cl = dfcell['layer#'].tolist()  ## cell was found in layers
        ct = dfcell['category'].tolist()

        checkfrom = tclist[0]-30
        if checkfrom < 0:
            checkfrom = 0
        checkto = tclist[0]+30
        if checkto > len(dfcell):
            checkto = len(dfcell)
        #print(f'[debug#254] check from {checkfrom} to {checkto}')
        for i in range(checkfrom, checkto):
            nratio, tcarea = aux.getIntersectionArea(cx[i], cy[i], cw[i], ch[i], tx, ty, tw, th)
            if nratio > 0.85:
                whichlayer = cl[i]
                celltype[whichlayer-1] = ct[i]
                tagscore[whichlayer-1] = [
                    float(dfcell.iloc[i]['trait_1']), float(dfcell.iloc[i]['trait_2']), float(dfcell.iloc[i]['trait_3']), 
                    float(dfcell.iloc[i]['trait_4']), float(dfcell.iloc[i]['trait_5']), float(dfcell.iloc[i]['trait_6']), 
                    float(dfcell.iloc[i]['trait_7']), float(dfcell.iloc[i]['trait_8']), float(dfcell.iloc[i]['trait_9']), 
                    float(dfcell.iloc[i]['trait_10']), float(dfcell.iloc[i]['trait_11']), float(dfcell.iloc[i]['trait_12']),
                    float(dfcell.iloc[i]['trait_13']), float(dfcell.iloc[i]['trait_14'])]
    
    return celltype, tagscore

###############################
##  analysis metadata to CSV
###############################
def saveTCellsMetadata2CSV(aixfname, allcells, aixmodel, modelver):
    if len(allcells) == 0:
        aux.printmsg(f'[ERROR] empty analysis metadata in {aixfname}')
        return
    # sort
    #allCells.sort(key=sortCategory)
    allcells.sort(key=lambda x: x['category'])
    #
    path_aix, file_aix = os.path.split(aixfname)
    shortname, extension = os.path.splitext(file_aix)
    pathmeta = f'{path_aix}\\metadata'
    if os.path.isdir(pathmeta) == False:
        os.mkdir(pathmeta)
    csvfname = f'{pathmeta}\\metadata_{shortname}_{aixmodel}_{modelver}.csv'
 
    with open(csvfname, 'w', newline='') as outcsv:
        if aixmodel == 'AIxURO':
            headcols = ['cellname', 'category', 'probability', 'score', 'ncratio', 'nucleusarea']
            tagscols = ['hyperchromasia', 'clumpedchromtin', 'irregularmembrane', 'pyknotic', 'lightnesseffect',
                        'dryingartifact', 'degenerated', 'smudged', 'unfocused', 'barenucleus', 'binuclei', 'normal', 
                        'fibrovascularcore', 'nuclearplemorphism' ]
        elif aixmodel == 'AIxTHY':
            headcols = ['cellname', 'category', 'probability', 'score', 'area'] 
            if modelver[:6] in ['2025.2']:
                architectureTraits = ['Papillary', 'NuclearCrowding', 'Microfollicles', 'FlatUniform']
                morphologicFeatures = ['NuclearEnlargement', 'MultinucleatedGiantCell', 'Degenerated', 'Normal']
                papillarythyroid = ['Pseudoinclusions', 'Grooving', 'MarginalMicronucleoli']
                eptheloid = ['ClumpingChromatin', 'ProminentNucleoli']
                medullarythyroid = ['Plasmacytoid', 'SaltAndPepper', 'Binucleation', 'Spindle']
                artifactEffects = ['LightnessEffect', 'DryingArtifact', 'Unfocused']
                tagscols = architectureTraits+morphologicFeatures+papillarythyroid+eptheloid+medullarythyroid+artifactEffects
            else:
                tagscols = ['microfollicles', 'papillae', 'palenuclei', 'grooving', 'pseudoinclusions', 'marginallyplaced', 'plasmacytoid', 'saltandpepper' ]
        fields = headcols+tagscols 
        ww = csv.DictWriter(outcsv, fieldnames=fields)
        ww.writeheader()
        for i in range(len(allcells)):
            thisrow = {}
            thisrow['cellname']        = allcells[i]['cellname']
            thisrow['category']        = af.getCategoryName(aixmodel, modelver, allcells[i]['category'])
            thisrow['probability']     = allcells[i]['probability']
            thisrow['score']           = allcells[i]['score']
            if aixmodel == 'AIxURO':
                thisrow['ncratio']     = allcells[i]['ncratio']
                thisrow['nucleusarea'] = allcells[i]['cellarea']
            elif aixmodel == 'AIxTHY':
                thisrow['area']        = allcells[i]['cellarea']
            #aux.printmsg(f'[DEBUG] traits#: {len(tagscols)}; {allcells[i]['traits']}')
            for j in range(len(allcells[i]['traits'])):
                thisrow[tagscols[j]] = allcells[i]['traits'][j] 
            ww.writerow(thisrow)

def saveAnalysisMetadata2CSV(whichModel, modelver, listaix, listavg):
    if len(listaix) == 0 or len(listavg) == 0:
        return
    path_aix, _ = os.path.split(listaix[0])
    csvfname = f'{path_aix}\\summary_of_analysis_metadata.csv'
    with open(csvfname, 'w', newline='') as outcsv:
        if whichModel == 'AIxURO':
            fields = ['aixfname', 'suspicious', 'atypical', 'benign', 'degenerated', 'modelversion', 'similaritydegree', 
                      'suspicious_avg_ncratio', 'suspicious_avg_nucarea', 'atypical_avg_ncratio', 'atypical_avg_nucarea',
                      'top24_ncratio', 'top24_nucarea']
        elif whichModel == 'AIxTHY':
            if modelver[:6] in ['2025.2']:
                fields = ['aixfname', 'modelversion', 'similaritydegree', 'follicular', 'oncocytic', 'epithelioid', 
                          'lymphocytes', 'histiocytes', 'colloid']
            else:
                fields = ['aixfname', 'modelversion', 'similaritydegree', 'follicular', 'hurthle', 'histiocytes',
                          'lymphocytes', 'colloid', 'multinucleated', 'psammoma']
        ww = csv.DictWriter(outcsv, fieldnames=fields)
        ww.writeheader()
        for i in range(len(listavg)):
            thisrow = {}
            _, thisaixname = os.path.split(listaix[i])
            thisrow['aixfname']          = thisaixname
            thisrow['modelversion']  = f'{whichModel} {listavg[i]['modelversion']}'
            thisrow['similaritydegree'] = listavg[i]['similaritydegree']
            if whichModel == 'AIxURO':
                thisrow['suspicious']    = listavg[i]['cellcount'][2]
                thisrow['atypical']      = listavg[i]['cellcount'][3]
                thisrow['benign']        = listavg[i]['cellcount'][4]
                thisrow['degenerated']   = listavg[i]['cellcount'][7]
                thisrow['suspicious_avg_ncratio'] = listavg[i]['avgsncratio']
                thisrow['suspicious_avg_nucarea'] = listavg[i]['avgsnucarea']
                thisrow['atypical_avg_ncratio']   = listavg[i]['avgancratio']
                thisrow['atypical_avg_nucarea']   = listavg[i]['avganucarea']
                thisrow['top24_ncratio']          = listavg[i]['topncratio']
                thisrow['top24_nucarea']          = listavg[i]['topnucarea']
            elif whichModel == 'AIxTHY':
                thisrow['follicular']    = listavg[i]['cellcount'][1]
                if modelver[:6] in ['2025.2']:
                    thisrow['oncocytic']      = listavg[i]['cellcount'][2]
                    thisrow['epithelioid']    = listavg[i]['cellcount'][3]
                    thisrow['lymphocytes']    = listavg[i]['cellcount'][4]
                    thisrow['histiocytes']    = listavg[i]['cellcount'][5]
                    thisrow['colloid']        = listavg[i]['cellcount'][6]
                else:
                    thisrow['hurthle']        = listavg[i]['cellcount'][2]
                    thisrow['histiocytes']    = listavg[i]['cellcount'][3]
                    thisrow['lymphocytes']    = listavg[i]['cellcount'][4]
                    thisrow['colloid']        = listavg[i]['cellcount'][5]
                    thisrow['multinucleated'] = listavg[i]['cellcount'][6]
                    thisrow['psammoma']       = listavg[i]['cellcount'][7]
            ww.writerow(thisrow)

def saveTraitsSummary2CSV(whichmodel, modelver, aixlist, taglist):
    if len(aixlist) == 0 or len(taglist) == 0:
        aux.printmsg(f'[ERROR] nothing in {os.path.dirname(aixlist[0])} to save to CSV', True)
        return
    if whichmodel not in ['AIxURO', 'AIxTHY']:
        aux.printmsg('[ERROR] unknown Model', True)
        return
    path_aix, _ = os.path.split(aixlist[0])
    csvfname = f'{path_aix}\\summary_of_traits.csv'
    with open(csvfname, 'w', newline='') as tagcsv:
        if whichmodel == 'AIxURO':
            fields = ['aixfname', 'S_T1', 'S_T2', 'S_T3', 'S_T1T2', 'S_T1T3', 'S_T2T3', 'S_T1T2T3', 
                      'A_T1', 'A_T2', 'A_T3', 'A_T1T2', 'A_T1T3', 'A_T2T3', 'A_T1T2T3', 
                      'TOP_T1', 'TOP_T2', 'TOP_T3', 'TOP_T1T2', 'TOP_T1T3', 'TOP_T2T3', 'TOP_T1T2T3']
        else:   # AIxTHY
            if modelver[:6] in ['2025.2']:
                fields = ['aixfname', 'Papillary', 'NuclearCrowding', 'Microfollicles', 'FlatUniform', 
                            'NuclearEnlargement', 'MultinucleatedGiantCell', 'Degenerated', 'Normal',
                            'Pseudoinclusions', 'Grooving', 'MarginalMicronucleoli',
                            'ClumpingChromatin', 'ProminentNucleoli', 
                            'Plasmacytoid', 'SaltAndPepper', 'Binucleation', 'Spindle', 
                            'LightnessEffect', 'DryingArtifact', 'Unfocused']
            else:
                fields = ['aixfname', 'microfollicles', 'papillae', 'palenuclei', 'grooving', 'pseudoinclusions', 
                          'marginallyplaced', 'plasmacytoid', 'saltandpepper']
        ww = csv.DictWriter(tagcsv, fieldnames=fields)
        ww.writeheader()
        for i in range(len(aixlist)):
            thisrow = {}
            _, thisaixname = os.path.split(aixlist[i])
            thisrow['aixfname'] = thisaixname
            if whichmodel == 'AIxURO':
                thisrow['S_T1']     = taglist[i][0]
                thisrow['S_T2']     = taglist[i][1]
                thisrow['S_T3']     = taglist[i][2]
                thisrow['S_T1T2']   = taglist[i][3]
                thisrow['S_T1T3']   = taglist[i][4]
                thisrow['S_T2T3']   = taglist[i][5]
                thisrow['S_T1T2T3'] = taglist[i][6]
                thisrow['A_T1']     = taglist[i][7]
                thisrow['A_T2']     = taglist[i][8]
                thisrow['A_T3']     = taglist[i][9]
                thisrow['A_T1T2']   = taglist[i][10]
                thisrow['A_T1T3']   = taglist[i][11]
                thisrow['A_T2T3']   = taglist[i][12]
                thisrow['A_T1T2T3'] = taglist[i][13]
                thisrow['TOP_T1']   = taglist[i][14]
                thisrow['TOP_T2']   = taglist[i][15]
                thisrow['TOP_T3']   = taglist[i][16]
                thisrow['TOP_T1T2'] = taglist[i][17]
                thisrow['TOP_T1T3'] = taglist[i][18]
                thisrow['TOP_T2T3'] = taglist[i][19]
                thisrow['TOP_T1T2T3'] = taglist[i][20]
            else:   # AIxTHY
                if modelver[:6] in ['2025.2']:
                    thisrow['Papillary']               = taglist[i][0]
                    thisrow['NuclearCrowding']         = taglist[i][1]
                    thisrow['Microfollicles']          = taglist[i][2]
                    thisrow['FlatUniform']             = taglist[i][3]
                    thisrow['NuclearEnlargement']      = taglist[i][4]
                    thisrow['MultinucleatedGiantCell'] = taglist[i][5]
                    thisrow['Degenerated']             = taglist[i][6]
                    thisrow['Normal']                  = taglist[i][7]
                    thisrow['Pseudoinclusions']        = taglist[i][8]
                    thisrow['Grooving']                = taglist[i][9]
                    thisrow['MarginalMicronucleoli']   = taglist[i][10]
                    thisrow['ClumpingChromatin']       = taglist[i][11]
                    thisrow['ProminentNucleoli']       = taglist[i][12]
                    thisrow['Plasmacytoid']            = taglist[i][13]
                    thisrow['SaltAndPepper']           = taglist[i][14]
                    thisrow['Binucleation']            = taglist[i][15]
                    thisrow['Spindle']                 = taglist[i][16]
                    thisrow['LightnessEffect']         = taglist[i][17]
                    thisrow['DryingArtifact']          = taglist[i][18]
                    thisrow['Unfocused']               = taglist[i][19]
                else:
                    thisrow['microfollicles']   = taglist[i][0]
                    thisrow['papillae']         = taglist[i][1]
                    thisrow['palenuclei']       = taglist[i][2]
                    thisrow['grooving']         = taglist[i][3]
                    thisrow['pseudoinclusions'] = taglist[i][4] 
                    thisrow['marginallyplaced'] = taglist[i][5]
                    thisrow['plasmacytoid']     = taglist[i][6]
                    thisrow['saltandpepper']    = taglist[i][7]
            ww.writerow(thisrow)





