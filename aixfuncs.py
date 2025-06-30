import os
import json, gzip
import auxfuncs as aux

## average of NC ratio and Nuclei area of suspicious/atypical cells
def getUROaverageOfSAcells(tclist):
    sumSncratio, sumAncratio = 0.0, 0.0
    sumSnucarea, sumAnucarea = 0, 0
    countS, countA = 0, 0
    for i in range(len(tclist)):
        if tclist[i]['category'] == 2:
            celltype = 'suspicious'
        elif tclist[i]['category'] == 3:
            celltype = 'atypical'
        else:
            continue
        nucleiArea = tclist[i]['cellarea']*tclist[i]['ncratio']
        if celltype == 'suspicious':
            sumSncratio += tclist[i]['ncratio']
            sumSnucarea += nucleiArea
            countS += 1
        else:
            sumAncratio += tclist[i]['ncratio']
            sumAnucarea += nucleiArea
            countA += 1
    if countS > 0:
        avgSncratio = sumSncratio / countS
        avgSnucarea = sumSnucarea / countS
    else:
        avgSncratio, avgSnucarea = 0.0, 0.0
    if countA > 0:
        avgAncratio = sumAncratio / countA
        avgAnucarea = sumAnucarea / countA
    else:
        avgAncratio, avgAnucarea = 0.0, 0.0
    return avgSncratio, avgSnucarea, avgAncratio, avgAnucarea

## count/analyze the cell information in AIxURO model
def getUROaverageOfTopCells(tclist, topNum=24, suspiciousOnly=True):
    acells = [] ## list of atypical cells
    scells = [] ## list of suspicious cells
    tcells = [] ## list of TOP number of cells to return
    for i in range(len(tclist)):
        if tclist[i]['category'] == 2 or tclist[i]['category'] == 3:
            thiscell = (tclist[i]['cellname'],
                        tclist[i]['score'],
                        tclist[i]['probability'],
                        tclist[i]['ncratio'],
                        tclist[i]['cellarea']*tclist[i]['ncratio'])
            if tclist[i]['category'] == 2:
                scells.append(thiscell)
            else:
                acells.append(thiscell)
    ## sort cell list
    scells.sort(key=lambda x: x[1], reverse=True)
    acells.sort(key=lambda x: x[1], reverse=True)
    ## TOP number of cells
    topCells = []
    cellCount = 0
    sumNCratio, sumNucarea = 0.0, 0.0
    ## 
    for i in range(len(scells)):
        sumNCratio += scells[i][3]
        sumNucarea += scells[i][4]
        cellCount += 1
        tcells.append(scells[i])
        if cellCount >= topNum:
            break
    if cellCount < topNum and suspiciousOnly == False:
        for i in range(len(acells)):
            sumNCratio += acells[i][3]
            sumNucarea += acells[i][4]
            cellCount += 1
            tcells.append(acells[i])
            if cellCount >= topNum:
                break
    if cellCount > 0:
        avgNCratio = sumNCratio / cellCount
        avgNucarea = sumNucarea / cellCount
    else:
        avgNCratio, avgNucarea = 0.0, 0.0
    return tcells, avgNCratio, avgNucarea

def getTHYtopCells(tclist, category):
    tcells = [] ## list of TOP number of cells to return
    for i in range(len(tclist)):
        if tclist[i]['category'] == category:
            tcells.append(tclist[i])
    tcells.sort(key=lambda x: x[1], reverse=True)
    return tcells

## count traits
def countNumberOfUROtraits(tclist, threshold=0.4):
    ''' 
    count the number of each trait in the cell list
    [0, 1, 2]   'hyperchromasia', 'clumpedchromtin', 'irregularmembrane', of suspicious cells
    [3]         'hyperchromasia' & 'clumpedchromtin' of suspicious cells
    [4]         'hyperchromasia' & 'irregularmembrane' of suspicious cells
    [5]         'clumpedchromtin' & 'irregularmembrane' of suspicious cells
    [6]         'hyperchromasia' & 'clumpedchromtin' & 'irregularmembrane' of suspicious celles
    [7 ~ 13]    same as above, but only for atypical cells
    [14 ~ 21]   same as above, but only for TOP number of cells
    '''
    traitCount = [0 for i in range(21)]
    howmany = len(tclist)
    if howmany == 0:
        aux.printmsg(f'[ERROR] empty cell list in countNumberOfUROtraits()')
        return traitCount
    slist = []
    for i in range(len(tclist)):
        category = tclist[i]['category']
        if category != 2 and category != 3:
            continue
        ioffset = 7 if category == 3 else 0
        celltraits = tclist[i]['traits']
        trait1 = True if celltraits[0] >= threshold else False
        trait2 = True if celltraits[1] >= threshold else False
        trait3 = True if celltraits[2] >= threshold else False
        if trait1:
            traitCount[0+ioffset] += 1
            if trait2:
                if trait3:
                    traitCount[6+ioffset] += 1
                else:
                    traitCount[3+ioffset] += 1
            else:
                if trait3:
                    traitCount[4+ioffset] += 1
        if trait2:
            traitCount[1+ioffset] += 1
            if trait3 and trait1 == False:
                traitCount[5+ioffset] += 1
        if trait3:
            traitCount[2+ioffset] += 1
        if category == 2:   ## suspicious cell
            celltraits = (tclist[i]['score'], tclist[i]['traits'][0], 
                          tclist[i]['traits'][1], tclist[i]['traits'][2])
            slist.append(celltraits)
    ## TOP24, only suspicious cells
    slist.sort(key=lambda x: x[0], reverse=True)
    top24 = 24 if len(slist) > 24 else len(slist)
    for i in range(top24):
        if slist[i][1] >= threshold:
            traitCount[14] += 1
    return traitCount

def countNumberOfTHYtraits(tclist, maxTraits, threshold=0.4):
    '''
    model 2024.2-0625
    cccccc
    model 2025.2-0526, 2025.2-0626
    Architecture Traits:
        'Papillary configuration', 'Nuclear crowding and overlapping', 'Microfollices', 'Falt/Uniform'
    Morphlogic features:
        'Nuclear enlargement', 'Multinucleated gaint cell', 'Degenrated', 'Normal'
    Papillary thyroid carcinoma traits:
        'Pseudoinclusions', 'Grooving', Marginal micronucleoli'
    Epithelioid carcinoma (metastasis) traits:
        'Clumping chromatin', 'Prominent nucleoli', 
    Medullary thyroid carcinoma traits:
        'Plasmacytoid', 'Salt and Papper chromatin', 'Binucleation', 'spindlle'
    Artifact effects:
        'LightnessEffect', 'DryingArtifact', 'Unfocused'
    '''
    traitCount = [0 for i in range(maxTraits)]
    howmany = len(tclist)
    if howmany == 0:
        aux.printmsg(f'[ERROR] empty cell list in countNumberOfTHYtraits()')
        return traitCount
    for i in range(howmany):
        celltraits = tclist[i]['traits']
        for j in range(len(tclist[i]['traits'])):
            if celltraits[j] >= threshold:
                traitCount[j] += 1
    return traitCount

## special case for decart 2.0.x ad 2.1.x
def specialCase(category):
    if category == 0:
        typename = 'benign'
    elif category == 3:
        typename = 'nuclei'
    elif category == 2:
        typename = 'suspicious'
    elif category == 1:
        typename = 'atypical'
    else:
        typename = 'unknown'
    return typename

def getCategoryName(whichmodel, whichversion, category, noModelArch=True):
    uroTypeName = ['background', 'nuclei', 'suspicious', 'atypical', 'benign',
                   'other', 'tissue', 'degenerated']
    thy2024Name = ['background', 'follicular', 'hurthle', 'histiocytes', 'lymphocytes',
                   'colloid', 'multinucleatedGaint', 'psammomaBodies']
    thy2025Name = ['background', 'follicular', 'oncocytic', 'epithelioid',
                   'lymphocytes', 'histiocytes', 'colloid']
    #whichmodel = aixinfo.get('Model', 'unknown')
    if whichmodel == 'AIxURO':
        typename = uroTypeName[category] if noModelArch else specialCase(category)
    elif whichmodel == 'AIxTHY':
        #whichversion = aixinfo.get('ModelVersion', 'unknown')
        if whichversion[:6] in ['2025.2']:
            typename = thy2025Name[category]
        else:   ## modelversion: 2024.2-0625
            typename = thy2024Name[category]
    else:
        typename = 'unknown'
        print(f'{aux.sNOW()}[ERROR] incorrect model:{whichmodel} in getCategoryName()')
    return typename

## Reads an AIX file and returns a dictionary with the model information.
def getModelInfoFromAIX(aixfile, save2json=False):
    gaix = gzip.GzipFile(mode='rb', fileobj=open(aixfile, 'rb'))
    aixdata = gaix.read()
    gaix.close()
    aixjson = json.loads(aixdata)
    ## save 2 json file for debugging
    if save2json:
        sortname = os.path.splitext(os.path.basename(aixfile))[0]
        with open(f'{sortname}.json', 'w') as jsonobj:
            json.dump(aixjson, jsonobj, indent=4)
    ## here is for decart version 2.x.x
    aixinfo = aixjson.get('model', {})
    aixcell = aixjson.get('graph', {})
    return aixinfo, aixcell

def getAIXModelVersion(aixfile):
    gaix = gzip.GzipFile(mode='rb', fileobj=open(aixfile, 'rb'))
    aixdata = gaix.read()
    gaix.close()
    aixjson = json.loads(aixdata)
    ## save 2 json file for debugging
    aixinfo = aixjson.get('model', {})
    aixModelName = aixinfo.get('Model', 'unknown')
    aixModelVersion = aixinfo.get('ModelVersion', 'unknown')
    return aixModelName, aixModelVersion

def getCellsInfoFromAIX(aixfile, mpp=None):
    aixinfo, aixcell = getModelInfoFromAIX(aixfile)
    whichmodel = aixinfo.get('Model', 'unknown')
    if whichmodel == 'AIxURO':
        ## return getAixuroCellInfo(aixfile)
        typeName = ['background', 'nuclei', 'suspicious', 'atypical', 'benign',
                    'other', 'tissue', 'degenerated']
        cellCount = [0 for i in range(len(typeName))]
        nulltags = [0.0 for _ in range(14)]
        ## get all the cell information
        allCells = []
        for jj in range(len(aixcell)):
            cbody = aixcell[jj][1].get('children', '')
            if cbody == '':
                continue
            for kk in range(len(cbody)):
                cdata = cbody[kk][1].get('data', '')
                if cdata == '':
                    continue
                thiscell = {}
                category = cdata.get('category', -1)
                if category >= 0 and category < len(typeName):
                    cellCount[category] += 1
                else:
                    print(f'{aux.sNOW()}[ERROR] {os.path.basename(aixfile)} has unknown cell type ID:{category}.')
                thiscell['cellname'] = cbody[kk][1]['name']
                #thiscell['category'] = typeName[category] if 'ModelArchitect' not in aixinfo else specialCase(category)
                thiscell['category'] = category
                thiscell['segments'] = cbody[kk][1]['segments']
                thiscell['ncratio']  = cdata.get('ncRatio', 0.0)
                if mpp is not None:
                    thiscell['cellarea'] = aux.calculateCellArea(thiscell['segments'], mpp)
                thiscell['probability'] = cdata.get('prob', 0.0)
                thiscell['score'] = cdata.get('score', 0.0)
                thiscell['traits'] = cdata.get('tags', nulltags)
                allCells.append(thiscell)
        cellsList = sorted(allCells, key=lambda x: (-x['category'], x['score']), reverse=True)
        ## check whether 'modelArch' is in the cell information, if yes, revised some categories
        if 'ModelArchitect' in aixinfo:  ## decart 2.0.x and decart 2.1.x
            numNuclei, numAtypical, numBenign = cellCount[3], cellCount[1], cellCount[0]
            cellCount[0], cellCount[4] = 0, numBenign
            cellCount[1], cellCount[3] = numNuclei, numAtypical
        return aixinfo, cellCount, cellsList
    elif whichmodel == 'AIxTHY':
        ##return getAixthyCellInfo(aixfile)
        if aixinfo['ModelVersion'][:6] in ['2025.2']:
            typeName = ['background', 'follicular', 'oncocytic', 'epithelioid', 'lymphocytes', 'histiocytes', 'colloid', 'unknown']
        else:
            typeName = ['background', 'follicular', 'hurthle', 'histiocytes', 'lymphocytes', 
                        'colloid', 'multinucleatedGaint', 'psammomaBodies']
        objCount = [0 for i in range(len(typeName))]
        nulltags = [0.0 for _ in range(20)]
        ## get all the cell information
        allCells = []
        for jj in range(len(aixcell)):
            cbody = aixcell[jj][1].get('children', '')
            if cbody == '':
                continue
            for kk in range(len(cbody)):
                cdata = cbody[kk][1].get('data', '')
                if cdata == '':
                    continue
                thiscell = {}
                category = cdata.get('category', -1)
                if category >= 0 and category < len(typeName):
                    objCount[category] += 1
                else:
                    print(f'{aux.sNOW()}[ERROR] {os.path.basename(aixfile)} has unknown cell type ID:{category}.')
                thiscell['cellname'] = cbody[kk][1]['name']
                #thiscell['category'] = typeName[category]
                thiscell['category'] = category
                thiscell['segments'] = cbody[kk][1]['segments']
                if mpp is not None:
                    thiscell['cellarea'] = aux.calculateCellArea(thiscell['segments'], mpp)
                thiscell['probability'] = cdata.get('prob', 0.0)
                thiscell['score'] = cdata.get('score', 0.0)
                thiscell['traits'] = cdata.get('tags', nulltags)
                allCells.append(thiscell)
        cellsList = sorted(allCells, key=lambda x: (-x['category'], x['score']), reverse=True)
        return aixinfo, objCount, cellsList
    else:
        print(f'{aux.sNOW()}[ERROR] {os.path.basename(aixfile)} is not analyzed by AIxURO or AIxTHY model.')
        return aixinfo, [], []

## get the analyzed cell information of AIxURO model
def getAixuroCellInfo(aixfile):
    aixinfo, aixcell = getModelInfoFromAIX(aixfile)
    whichmodel = aixinfo.get('Model', 'unknown')
    if whichmodel != 'AIxURO':
        print(f'{aux.sNOW()}[ERROR] {os.path.basename(aixfile)} is not analyzed by AIxURO model.')
        return aixinfo, [], []
    typeName = ['background', 'nuclei', 'suspicious', 'atypical', 'benign',
                'other', 'tissue', 'degenerated']
    traitName = ['hyperchromasia', 'clumpedchromtin', 'irregularmembrane', 'pyknotic', 'lightnesseffect', 
                 'dryingartifact', 'degenerated', 'smudged', 'unfocused', 'unfocused', 'binuclei',
                 'normal', 'FibrovascularCore', 'NuclearPlemorphism']
    cellCount = [0 for i in range(len(typeName))]
    nulltags = [0.0 for _ in range(14)]
    ## get all the cell information
    allCells = []
    for jj in range(len(aixcell)):
        cbody = aixcell[jj][1].get('children', '')
        if cbody == '':
            continue
        for kk in range(len(cbody)):
            cdata = cbody[kk][1].get('data', '')
            if cdata == '':
                continue
            thiscell = {}
            category = cdata.get('category', -1)
            if category >= 0 and category < len(typeName):
                cellCount[category] += 1
            else:
                print(f'{aux.sNOW()}[ERROR] {os.path.basename(aixfile)} has unknown cell type ID:{category}.')
            thiscell['cellname'] = cbody[kk][1]['name']
            thiscell['category'] = typeName[category] if 'ModelArchitect' not in aixinfo else specialCase(category)
            thiscell['segments'] = cbody[kk][1]['segments']
            thiscell['ncratio']  = cdata.get('ncRatio', 0.0)
            thiscell['probability'] = cdata.get('prob', 0.0)
            thiscell['score'] = cdata.get('score', 0.0)
            thiscell['traits'] = cdata.get('tags', nulltags)
            allCells.append(thiscell)
    ## check whether 'modelArch' is in the cell information, if yes, revised some categories
    if 'ModelArchitect' in aixinfo:  ## decart 2.0.x and decart 2.1.x
        numNuclei, numAtypical, numBenign = cellCount[3], cellCount[1], cellCount[0]
        cellCount[0], cellCount[4] = 0, numBenign
        cellCount[1], cellCount[3] = numNuclei, numAtypical

    return aixinfo, cellCount, allCells

## get the analyzed cell information of AIxURO model
def getAixthyCellInfo(aixfile):
    aixinfo, aixcell = getModelInfoFromAIX(aixfile)
    whichmodel = aixinfo.get('Model', 'unknown')
    if whichmodel != 'AIxTHY':
        print(f'{aux.sNOW()}[ERROR] {os.path.basename(aixfile)} is not analyzed by AIxTHY model.')
        return aixinfo, [], []
    modelversion = aixinfo.get('ModelVersion', 'unknown')
    if modelversion[:6] in ['2025.2']:
        typeName = ['background', 'follicular', 'oncocytic', 'epithelioid', 'lymphocytes', 'histiocytes', 'colloid', 'unknown']
        traitName = ['Papillary', 'NuclearCrowding', 'Microfollicles', 'FlatUniform',       ## architectureTraits
                     'NuclearEnlargement', 'MultinucleatedGiantCell', 'Degenerated', 'Normal',  ## morphologicFeatures
                     'Pseudoinclusions', 'Grooving', 'MarginalMicronucleoli',  ## papillarythyroid
                     'ClumpingChromatin', 'ProminentNucleoli',  ##  eptheloid
                     'Plasmacytoid', 'SaltAndPepper', 'Binucleation', 'Spindle',    ## medullarythyroid
                     'LightnessEffect', 'DryingArtifact', 'Unfocused']                          ##  artifactEffects
        traitName = []
    else:
        typeName = ['background', 'follicular', 'hurthle', 'histiocytes', 'lymphocytes', 'colloid', 'multinucleatedGaint', 'psammomaBodies']
        traitName = ['microfollicles', 'papillae', 'palenuclei', 'grooving', 'pseudoinclusions', 
                 'marginallyplaced', 'plasmacytoid', 'saltandpepper', 'FibrovascularCore' ]
    objType = [i for i in range(len(typeName))]
    objCount = [0 for i in range(len(typeName))]
    nulltags = [0.0 for _ in range(20)]
    ## get all the cell information
    allCells = []
    for jj in range(len(aixcell)):
        cbody = aixcell[jj][1].get('children', '')
        if cbody == '':
            continue
        for kk in range(len(cbody)):
            cdata = cbody[kk][1].get('data', '')
            if cdata == '':
                continue
            thiscell = {}
            category = cdata.get('category', -1)
            if category >= 0 and category < len(typeName):
                objCount[category] += 1
            else:
                print(f'{aux.sNOW()}[ERROR] {os.path.basename(aixfile)} has unknown cell type ID:{category}.')
            thiscell['cellname'] = cbody[kk][1]['name']
            thiscell['category'] = typeName[category]
            thiscell['segments'] = cbody[kk][1]['segments']
            thiscell['probability'] = cdata.get('prob', 0.0)
            thiscell['score'] = cdata.get('score', 0.0)
            thiscell['traits'] = cdata.get('tags', nulltags)
            allCells.append(thiscell)
    return aixinfo, objCount, allCells

'''
cell coverage analysis
'''
def processCellCoverage(aixpath, tcTypes, bestZ, bCalcBren=False):
    pass

