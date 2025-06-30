################################################################################
# do inference by DeCart using Git-CMD on Windows
# 
#   v7.00, 2025-06-18, Philip Wu, restructure
#   v6.00, 2024-10-08, Philip Wu, add AIxTHY model
#   v5.00, 2024-03-27, Philip Wu, customize for gooey GUI
#   v4.00, 2024-01-24, Philip Wu, add average N/C rario, nucleus area and TOP24
#   v3.00, 2023-09-21, Philip Wu, add an option to work using Git Bash
#   v2.00, 2023-09-13, Philip Wu, inference all the WSI files in the specified folder
#   v1.00, 2023-08-10, Philip Wu
# Copyrights(c) 2023-2025, AIxMed Inc.
################################################################################
import os, glob
import shutil
from datetime import datetime
from pyunpack import Archive
from func_timeout import func_set_timeout, FunctionTimedOut
import yaml
import aixfuncs as af
import auxfuncs as aux
import medfuncs as mf
import csvfuncs as cf

def updateDeCartConfig(thismodel):
    configYaml = 'c:\\ProgramData\\DeCart\\config.yaml'
    with open(configYaml, 'r') as curyaml:
        conf = yaml.load(curyaml, Loader=yaml.FullLoader)
    if conf['preset'].lower() != thismodel.lower():
        conf['preset'] = thismodel.lower()
        with open(configYaml, 'w') as newyaml:
            yaml.dump(conf, newyaml)
        return True
    return False

def collectAnaysisMetadata(whichWSI):
    thismeta = {}
    medjson = mf.getMetadataFromMED(f'{whichWSI}.med')
    aix_model, cellCount, cellsList = af.getCellsInfoFromAIX(f'{whichWSI}.aix', medjson['MPP'])
    thismeta['wsifname'] = os.path.split(whichWSI)[1]
    thismeta['scanner'] = mf.readMakerAndDeviceFromMED(medjson)
    thismeta['mpp'], thismeta['icc'] = medjson['MPP'], medjson.get('IccProfile', '')
    thismeta['width'], thismeta['height'] = medjson['Width'], medjson['Height']
    thismeta['sizez'] = medjson['SizeZ']
    thismeta['bestfocusayer'] = medjson.get('BestFocusLayer', 0)
    thismeta['modelname'], thismeta['modelversion'] = aix_model['Model'], aix_model['ModelVersion']
    thismeta['cellCount'] = cellCount
    thismeta['similarity'] = aix_model.get('SimilarityDegree', 0.0)
    if aix_model['Model'] == 'AIxURO':
        thismeta['savgncratio'], thismeta['savgnucarea'], thismeta['aavgncratio'], thismeta['aavgnucarea'] = af.getUROaverageOfSAcells(cellsList)
        _, thismeta['avgtop24ncratio'], thismeta['avgtop24nucarea'] = af.getUROaverageOfTopCells(cellsList)
    return thismeta

@func_set_timeout(86400)    ## in case of model inference takes too long time for more than 11 layers
def gotoModelInference(wsifiles, bin_decart, doneFolder, metaRecords, bVer1Model=False):
    if os.environ.get('DC_SINGLE_PLANE', None) != None:
        os.environ.pop('DC_SINGLE_PLANE')
    spos = bin_decart.index('decart')
    decart_version = os.path.split(bin_decart)[0][spos+6:]
    if bVer1Model == False:
        bin_decart += '-verbose -w'
    for ii, wsf in enumerate(wsifiles):
        workpath, wsifname = os.path.split(wsf)
        shortname, extension = os.path.splitext(wsifname)
        if extension.lower() in ['.tif', '.tiff']:
            os.environ['DC_EXTENDED_FORMAT'] = '1'
        cmd_decart = f'{bin_decart} {wsf}'
        aux.printmsg(f'[INFO] {cmd_decart}', 'INFO')
        sdt = datetime.now()
        aux.printmsg(f'[INFO] Start model inference for {wsf} ({ii+1} of {len(wsifiles)}) from {sdt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} ...', 'INFO')
        os.system(cmd_decart)
        edt = datetime.now()
        aux.printmsg(f'[INFO] Finish model inference for {wsf} at {edt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}...', 'INFO')
        analysis_timestamp = edt.timestamp() - sdt.timestamp()
        ## check .med file
        medfile = os.path.join(workpath, f'.{doneFolder}\\{shortname}.med')
        aixfile = os.path.join(workpath, f'.{doneFolder}\\{shortname}.aix')
        if not os.path.exists(medfile) or not os.path.exists(aixfile):
            aux.printmsg(f'[ERROR] {medfile} does not exist!', 'ERROR')
            return
        ## collect model analysis metadata
        thismeta = collectAnaysisMetadata(os.path.splitext(medfile)[0])
        #### filesize
        if extension.lower() == '.mrxs':
            mrxspath = os.path.join(workpath, shortname)
            totalfsize = sum(os.path.getsize(f'{mrxspath}\\{fd}') for fd in os.listdir(mrxspath) if os.path.isfile(f'{mrxspath}\\{fd}'))
        else:
            totalfsize = os.path.getsize(wsf)
        wsifsize = round(totalfsize/(1024*1024), 4)     ## in MB
        medfsize = round((os.path.getsize(medfile)+os.path.getsize(aixfile))/(1024*1024), 4)     ## in MB
        thismeta['wsifname'] = wsifname
        thismeta['wsifsize'] = wsifsize
        thismeta['medfsize'] = medfsize
        thismeta['decart_version'] = decart_version
        thismeta['execution_date'] = int(sdt.timestamp())
        thismeta['analysis_timestamp'] = analysis_timestamp
        metaRecords.append(thismeta)

def doModelInference(wsipath, modelname='AIxURO', decart_version='2.7.4', bmetadata=True):
    if not os.path.exists(wsipath):
        aux.printmsg(f'[ERROR] {wsipath} does not exist!')
        return
    ## configuration settings
    args = aux.getConfig()
    binpath = args['binpath']
    dir_decart = os.path.join(binpath, f'decart{decart_version}')
    bVer1Model = True if decart_version in ['1.5.4', '1.6.3', '2.0.7', '2.1.2'] else False
    doneFolder = '' if decart_version[:5] in ['2.7.3', '2.7.4', '2.7.5'] else '\\done'
    cmd_decart = f'{dir_decart}\\decart.exe '
    medaix_metadata = []    ## metadata of model inference analysis results
    ## get the list of WSI files to be processed
    wsifiles, medfiles, zipfiles = [], [], []    ## zip files for DICOM format or zipped MRXS format
    wsilist = glob.glob(os.path.join(wsipath, '*'))
    for _, fd in enumerate(wsilist):
        if os.path.isfile(fd) == False:
            continue
        wsiformat = os.path.splitext(fd)[1][1:].lower()
        #print({fd}, {wsiformat})
        if wsiformat in ['svs', 'ndpi', 'mrxs', 'bif', 'tif', 'tiff']:
            wsifiles.append(aux.replaceSpace2underscore(fd))
        elif wsiformat == 'zip':
            zipfiles.append(aux.replaceSpace2underscore(fd))
        elif wsiformat == 'med':
            medfiles.append(aux.replaceSpace2underscore(fd))
    if len(wsifiles) == 0 and len(zipfiles) == 0 and len(medfiles) == 0:
        aux.printmsg(f'[ERROR] No WSI files found in {wsipath}!')
        return
    ## do model inference
    #### update c:\programdata\decart\config.yaml, if needs
    if updateDeCartConfig(modelname):
        aux.printmsg(f'[INFO] Update DeCart model preset to {modelname}', 'INFO')
    #### do inference for each WSI file, piority: WSI > zip > med    
    if bVer1Model:
        pass
    else:
        #cmd_decart += '-verbose -w '
        howmanywsi = len(wsifiles)
        if howmanywsi > 0:
            aux.printmsg(f'[INFO] Start model inference using decart{decart_version} model:{modelname} for {howmanywsi} WSI files...')
            gotoModelInference(wsifiles, cmd_decart, doneFolder, medaix_metadata)
        howmanyzip = len(zipfiles)
        if howmanyzip > 0:
            aux.printmsg(f'[INFO] Start model inference using decart{decart_version} model:{modelname} for {howmanyzip} ZIP files...')
            gotoModelInference(zipfiles, cmd_decart, doneFolder, medaix_metadata)
        howmanymed = len(medfiles)
        if howmanymed > 0:
            aux.printmsg(f'[INFO] Start model inference using decart{decart_version} model:{modelname} for {howmanymed} MED files...')
            gotoModelInference(medfiles, cmd_decart, doneFolder, medaix_metadata)

    ## save metadata of model inference analysis results
    if len(medaix_metadata) > 0 and bmetadata:
        cf.saveInferenceResult2CSV(medaix_metadata, wsipath)
    aux.printmsg(f'[INFO] {modelname} model inference {wsipath} completed!', 'INFO')

########
##  get analysis metadata, summarize to CSV
########
def collectAnaysisMetadata(workpath, thismpp=0.0):
    medlist = glob.glob(os.path.join(workpath, '*.med'))
    if len(medlist) > 0:
        medjson = mf.getMetadataFromMED(medlist[0])
        thismpp = medjson.get('MPP', 0.0)

    if thismpp == 0.0:
        in_mpp = input('Please enter the MPP data for these .aix files: ')
        try:
            thismpp = float(in_mpp)
        except:
            thismpp = 0.0
            aux.printmsg('[ERROR] Your input data is not a float data.', uilog=True)
    cellmeta, tagsmeta = [], []
    aixlist = glob.glob(os.path.join(workpath, '*.aix'))
    if thismpp != 0.0:
        for aixfile in aixlist:
            ## collect analysis metadata
            thismeta = {}
            aixinfo, cellcount, cellslist = af.getCellsInfoFromAIX(aixfile, mpp=thismpp)
            modelname, modelversion = aixinfo['Model'], aixinfo['ModelVersion']
            thismeta['modelname'], thismeta['modelversion'] = modelname, modelversion
            thismeta['cellcount'] = cellcount
            thismeta['similaritydegree'] = aixinfo.get('SimilarityDegree', '')
            if modelname == 'AIxURO':
                thismeta['avgsncratio'], thismeta['avgsnucarea'], thismeta['avgancratio'], thismeta['avganucarea'] = af.getUROaverageOfSAcells(cellslist)
                _, thismeta['topncratio'], thismeta['topnucarea'] = af.getUROaverageOfTopCells(cellslist, topNum=24, suspiciousOnly=True)
            cellmeta.append(thismeta)
            #### save metadata to CSV
            cf.saveTCellsMetadata2CSV(aixfile, cellslist, modelname, modelversion)
            ## collect traits information
            if modelname == 'AIxURO':
                thistrait = af.countNumberOfUROtraits(cellslist, threshold=0.4)
            else:
                thistrait = af.countNumberOfTHYtraits(cellslist, 20, threshold=0.4)
            tagsmeta.append(thistrait)
        ## summary of analysis metadata
        cf.saveAnalysisMetadata2CSV(modelname, modelversion, aixlist, cellmeta)
        cf.saveTraitsSummary2CSV(modelname, modelversion, aixlist, tagsmeta)
        ## summary of traits
        aux.printmsg('[INFO] analysis metadata and traits summary saved to CSV', True)

########
##  extract every single layers from mutiple layers of .med file
########
def extractSingleLayersFromMultiLayersMED(medfname, dstpath, modelname=''):
    args = aux.getConfig()
    binasar = args['exe_rasar']
    multimed = aux.replaceSpace2underscore(medfname)
    dzipath = os.path.join(dstpath, 'dzi')
    if os.path.isdir(dzipath) == False:
        os.makedirs(dzipath)
    aux.printmsg(f'[INFO] extract single layers from {os.path.basename(medfname)} to {dstpath}')
    tsfrom = datetime.now().timestamp()
    TotalLayers, BestzLayer = mf.updateMEDmetadata2singleLayer(multimed, dzipath)
    medprefix = os.path.splitext(os.path.split(multimed)[1])[0]
    for lidx in range(TotalLayers):
        mf.extractDZIdataFromMED(multimed, lidx, dzipath)
        bz = '_bestz_' if lidx == BestzLayer else '_'
        thismed = os.path.join(dstpath, f'{medprefix}{bz}z{lidx:02}.med')
        cmd_packmed = f'{binasar} pack {dzipath} {thismed}'
        os.system(cmd_packmed)
        aux.printmsg(f'[INFO] {os.path.basename(thismed)} is generated!')
        # remove Z0_files, Z0.dzi, Z0.dz
        if os.path.isdir(f'{dzipath}\\Z0_files'):
            shutil.rmtree(f'{dzipath}\\Z0_files')
        if os.path.isfile(f'{dzipath}\\Z0.dzi'):
            os.remove(f'{dzipath}\\Z0.dzi')
        if os.path.isfile(f'{dzipath}\\Z0.dz'):
            os.remove(f'{dzipath}\\Z0.dz')
    ## remove dzi folder
    shutil.rmtree(dzipath)
    tsstop = datetime.now().timestamp()
    aux.printmsg(f'[INFO] took {aux.timestampDelta2String(tsstop-tsfrom)} to extract all single layers from {os.path.basename(medfname)}')
    if modelname in ['AIxURO', 'AIxTHY']:
        tsfrom = datetime.now().timestamp()
        updateDeCartConfig(modelname)
        decart_version = args['decart_ver']
        doModelInference(dstpath, modelname, decart_version, bmetadata=False)
        tsstop = datetime.now().timestamp()
        aux.printmsg(f'[INFO] took {aux.timestampDelta2String(tsstop-tsfrom)} to analyze all {TotalLayers} single layers from {os.path.basename(medfname)}')
        


