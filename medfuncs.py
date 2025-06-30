import os, glob
import shutil
import asarlib
import json

import auxfuncs as aux

## retrieve necessary metadata from metadata.json in a .med file
def readMakerAndDeviceFromMED(medjson):
    maker = medjson.get('Vndor', '')
    scanner = medjson['Scanner'] if maker == '' else f'{maker}'
    if medjson.get('ScannerModel', '') != '':
        scanner += f' ({medjson["ScannerModel"]})'
    elif medjson.get('ScannerType', '') != '':
        scanner += f' ({medjson["ScannerType"]})'
    elif medjson.get('ScanScopeId', '') != '':
        scanner += f' ({medjson["ScanScopeId"]})'
    elif medjson.get('ScannerModel', '') != '':
        scanner += f' ({medjson["ScannerModel"]})'
    return scanner

def getMetadataFromMED(medfile):
    with asarlib.AsarFile(medfile) as thismed:
        mdata = thismed.read_file('metadata.json')
    metajson = json.loads(mdata)
    return metajson

def updateMEDmetadata2singleLayer(medfile, dzipath):
    medjson = getMetadataFromMED(medfile)
    sizeZ = medjson.get('SizeZ', 1)
    if sizeZ == 1:
        aux.printmsg(f'[ERROR] {os.path.basename(medfile)} dose not contain multiple layers of images', True)
        return sizeZ, 0
    bestZ = medjson.get('BestFocusLayer', -1)
    if bestZ == -1:
        aux.printmsg(f'[ERROR] missing BestFocusLayer in metadata of {os.path.basename(medfile)}', True)
        return sizeZ, 0
    medjson.pop('BestFocusLayer')
    levelcount = medjson.get('LevelCount', 0)
    if levelcount > 0:
        medjson['LevelCount'] = 0
    medjson['IndexZ'] = [0]
    medjson['SizeZ']  = 1
    ## update metadata.json
    metafile = os.path.join(dzipath, 'metadata.json')
    with open(metafile, 'w', encoding='utf-8') as newmeta:
        json.dump(medjson, newmeta)
    aux.printmsg(f'[INFO] metadata.json for single layer was updated')
    return sizeZ, bestZ

def extractDZIdataFromMED(medfile, layer, dzipath):
    with asarlib.AsarFile(medfile) as thismed:
        ## extract associated file
        asslist = thismed.listdir()
        dz_existed = False
        for _, associate in enumerate(asslist):
            if 'Z' not in associate and associate != 'metadata.json':
                thismed.extract_file(associate, dzipath)
            if f'Z{layer}.dz' == associate:
                dz_existed = True
        thismed.extract(f'Z{layer}_files', dzipath)
        if dz_existed:
            thismed.extract_file(f'Z{layer}.dz', dzipath)
        thismed.extract_file(f'Z{layer}.dzi', dzipath)
        os.rename(os.path.join(dzipath, f'Z{layer}_files'), os.path.join(dzipath, 'Z0_files'))
        os.rename(os.path.join(dzipath, f'Z{layer}.dzi'), os.path.join(dzipath, 'Z0.dzi'))
        if dz_existed:
            os.rename(os.path.join(dzipath, f'Z{layer}.dz'), os.path.join(dzipath, 'Z0.dz'))

'''
## revise metadata.json of a.med file, 
## for now, only for packing multiple.med files to a single.med file
def reviseMetadataJson(metafile, workpath, zstack):
    with open(metafile, 'r', encoding='utf-8') as fmeta:
        metajson = json.load(fmeta)
    metajson['SizeZ'] = zstack
    metajson['LevelCount'] = zstack+1
    metajson['IndexZ'] = [i for i in range(1, zstack+1)]
    metajson['BestFocusLayer'] = zstack // 2
    ## save revised metadata.json
    metafile = os.path.join(workpath, 'metadata.json')  ## save to workpath, not the original.med file roo
    with open(metafile, 'w', encoding='utf-8') as newmeta:
        json.dump(metajson, newmeta)
'''
## pack multiple .med files to be a single .med file
##   input: folder containing .med files, number of layers, separation distance,
##          original separatio step (defaut: 1um)
##  [note]: .med file should be unpacked before this processing
def packMultiLayers2singleMED(medfolder, dstfolder, s_layer, e_layer, step_um):
    medfiles = glob.glob(os.path.join(medfolder, '*.med'))
    if len(medfiles) == 0:
        print('{aux.sNOW()}[ERROR] No .med files found in the folder.')
        return
    howmany = len(medfiles)
    ## check multiple.med files, can't be packed if missing something
    if e_layer-s_layer >= howmany:
        errmsg = f'{aux.sNOW()}[ERROR] Something wrong, missing layers in the folder.'
    elif (e_layer-s_layer) % 2 != 0:
        errmsg = f'{aux.sNOW()}[ERROR] only pack odd integer of layers'
    else:
        errmsg = ''
    if errmsg != '':
        print(errmsg)
        return    
    # revise metadata.json from multiple to single .med file
    dzipath = os.path.join(dstfolder, 'dzi')
    if os.path.isdir(dzipath) == False:
        os.mkdir(dzipath)
    # extract (not webp) files from .med file
    with asarlib.AsarFile(medfiles[0]) as thismed:
        asslist = thismed.listdir()
        for i, associate in enumerate(asslist):
            if 'Z' not in associate:
                thismed.extract_file(associate, dst=dzipath)
    ## revise metadata.json
    oldmetafile = os.path.join(dzipath, 'metadata.json')
    zstack = int((e_layer-s_layer)/step_um)+1
    ##--reviseMetadataJson(oldmetafile, dzipath, zstack)
    with open(oldmetafile, 'r', encoding='utf-8') as fmeta:
        metajson = json.load(fmeta)
    metajson['SizeZ'] = zstack
    metajson['LevelCount'] = zstack+1
    metajson['IndexZ'] = [i for i in range(1, zstack+1)]
    metajson['BestFocusLayer'] = zstack // 2
    ## save revised metadata.json
    metafile = os.path.join(dzipath, 'metadata.json')  ## save to workpath, not the original.med file roo
    with open(metafile, 'w', encoding='utf-8') as newmeta:
        json.dump(metajson, newmeta)
    ##
    zidx = zstack-1
    med_prefix = os.path.splitext(os.path.basename(medfiles[0]))[0][:-2]
    for i in range(e_layer, s_layer-1, 0-step_um):
        thismed = f'{medfolder}\\{med_prefix}{i:02}.med'
        ## retrieve Z0_files and Z0.dzi from.med file
        with asarlib.AsarFile(thismed) as unpackmed:
            unpackmed.extract('Z0_files', dzipath)
            unpackmed.extract_file('Z0.dzi', dzipath)
        ## rename Z0_files to Z{zidx}_files
        os.rename(os.path.join(dzipath, 'Z0_files'), os.path.join(dzipath, f'Z{zidx}_files'))
        ## rename Z0.dzi to Z{zidx}.dzi
        os.rename(os.path.join(dzipath, 'Z0.dzi'), os.path.join(dzipath, f'Z{zidx}.dzi'))
        zidx -= 1
    ## pack all files to a single.med file
    args = aux.getConfig()
    rasar = args['exe_rasar']
    medfile = os.path.join(dstfolder, f'{med_prefix[:-2]}-{zstack}L{step_um}um.med')
    print(f'{aux.sNOW()}[INFO] Packing {zstack} .med files to {os.path.basename(medfile)}...')
    packMED = f'{rasar} pack {dzipath} {medfile}'
    os.system(packMED)
    print(f'{aux.sNOW()}[INFO] removing temporary dzi folder...')
    shutil.rmtree(dzipath)
    print(f'{aux.sNOW()}[INFO] {os.path.basename(medfile)} completed!')

## extract partial layers of images, then pack to a single.med file 
def extractPartialLayers2singleMED(medfname, dstfolder, s_layer, e_layer, step_um):
    ## parameters settings
    args = aux.getConfig()
    #dzi_tmp = os.path.join(dstfolder 'dzi')
    rasar = args['exe_rasar']
    ## replace ' ' with '_' in the .med filename
    thismed = aux.replaceSpace2underscore(medfname)
    dzi_tmp = os.path.join(dstfolder, 'dzi')
    if not os.path.exists(dzi_tmp):
        os.mkdir(dzi_tmp)
    ## extraact necessary files/folders from .med, using asarlib
    if (e_layer-s_layer) % step_um != 0:
        print(f'{aux.sNOW()}[ERROR] The number of layers is not a multiple of the step size.')
        return
    zstack = int((e_layer-s_layer)/step_um) + 1
    try:
        with asarlib.AsarFile(thismed) as unpackmed:
            mdata = unpackmed.read_file('metadata.json')
            metajson = json.loads(mdata)
            bestz = metajson.get('BestFocusLayer', 0)
            nlayers = metajson.get('SizeZ')
            if bestz == 0:
                print(f'{aux.sNOW()}[WARNING] {thismed} is a singe layer image.')
            else:
                metajson['BestFocusLayer'] = zstack // 2    ## remove BestFocusLayer
                metajson['LevelCount'] = zstack
                metajson['SizeZ'] = zstack
                metajson['IndexZ'] = [i for i in range(zstack)]
                ## rewrite metadata.json for bestz layer
                with open(os.path.join(dzi_tmp, 'metadata.json'), 'w', encoding='utf-8') as fmeta:
                    json.dump(metajson, fmeta)
            ## extract associate files from.med
            dirwalk = unpackmed.listdir()
            stidx = nlayers*3 if f'Z{bestz}.dz' in dirwalk else nlayers*2
            for i in range(stidx, len(dirwalk)):
                if dirwalk[i] == 'metadata.json' or 'Z' in dirwalk[i]:
                    continue
                unpackmed.extract_file(dirwalk[i], dzi_tmp)
            ## extract webp data of bestz layer
            zidx = zstack-1
            for i in range(e_layer, s_layer-1, 0-step_um):
                unpackmed.extract(f'Z{i}_files', dzi_tmp)
                unpackmed.extract_file(f'Z{i}.dzi', dzi_tmp)
                os.rename(os.path.join(dzi_tmp, f'Z{i}_files'), os.path.join(dzi_tmp, f'Z{zidx}_files'))
                os.rename(os.path.join(dzi_tmp, f'Z{i}.dzi'), os.path.join(dzi_tmp, f'Z{zidx}.dzi'))
                if f'Z{i}.dz' in dirwalk:
                    unpackmed.extract_file(f'Z{i}.dz', dzi_tmp)
                    os.rename(os.path.join(dzi_tmp, f'Z{i}.dz'), os.path.join(dzi_tmp, f'Z{zidx}.dz'))
                zidx -= 1
    except Exception as e:
        print(f"{aux.sNOW()}[ERROR] An unexpected error occurred while calling asarlib.AsarFle(): {e}")
        return
    ## no action if bestz is 0
    if bestz == 0:
        return
    ## pack dzi to a single.med file
    medprefixname = os.path.splitext(os.path.basename(thismed))[0]
    medfname = f'{dstfolder}\\{medprefixname}-{zstack}L{step_um}um.med'
    print(f'{aux.sNOW()}[INFO] Packing {dzi_tmp} to {os.path.basename(medfname)}...')
    packMED = f'{rasar} pack {dzi_tmp} {medfname}'
    os.system(packMED)
    print(f'{aux.sNOW()}[INFO] {os.path.basename(medfname)} completed! removing temporary dzi folder...')
    shutil.rmtree(dzi_tmp)
    return

## extract bestz layer from multiple layers of .med file (using asarlib)
def extractBestzFromMED(medfname):
    ## parameters settings
    args = aux.getConfig()
    dzi_tmp = os.path.join(args['workdir'], 'dzi')
    rasar = args['exe_rasar']
    ## replace ' ' with '_' in the .med filename
    thismed = aux.replaceSpace2underscore(medfname)
    if not os.path.exists(dzi_tmp):
        os.makedirs(dzi_tmp)
    ## extraact necessary files/folders from .med, using asarlib
    try:
        with asarlib.AsarFile(thismed) as unpackmed:
            mdata = unpackmed.read_file('metadata.json')
            metajson = json.loads(mdata)
            bestz = metajson.get('BestFocusLayer', 0)
            if bestz == 0:
                print(f'{aux.sNOW()}[WARNING] {thismed} is a singe layer image.')
            else:
                metajson.pop('BestFocusLayer')  ## remove BestFocusLayer
                if metajson.get('LevelCount') != None:
                    metajson['LevelCount'] = 0
                zstack = metajson.get('SizeZ')
                if zstack != None:
                    metajson['SizeZ'] = 0
                if metajson.get('IndexZ') != None:
                    metajson['IndexZ'] = [0]
                ## rewrite metadata.json for bestz layer
                with open(os.path.join(dzi_tmp, 'metadata.json'), 'w', encoding='utf-8') as fmeta:
                    json.dump(metajson, fmeta)
                ## extract webp data of bestz layer
                dirwalk = unpackmed.listdir()
                unpackmed.extract(f'Z{bestz}_files', dzi_tmp)
                unpackmed.extract_file(f'Z{bestz}.dzi', dzi_tmp)
                os.rename(os.path.join(dzi_tmp, f'Z{bestz}_files'), os.path.join(dzi_tmp, 'Z0_files'))
                os.rename(os.path.join(dzi_tmp, f'Z{bestz}.dzi'), os.path.join(dzi_tmp, 'Z0.dzi'))
                if f'Z{bestz}.dz' in dirwalk:
                    unpackmed.extract_file(f'Z{bestz}.dz', dzi_tmp)
                    os.rename(os.path.join(dzi_tmp, f'Z{bestz}.dz'), os.path.join(dzi_tmp, 'Z0.dz'))
                stidx = zstack*3 if f'Z{bestz}.dz' in dirwalk else zstack*2
                for i in range(stidx, len(dirwalk)):
                    if dirwalk[i] == 'metadata.json':
                        continue
                    unpackmed.extract_file(dirwalk[i], dzi_tmp)
    except Exception as e:
        print(f"{aux.sNOW()}[ERROR] An unexpected error occurred while calling asarlib.AsarFle(): {e}")
        return
    ## pack dzi to a single.med file
    medprefixname = os.path.splitext(thismed)[0]
    bestzmed = medprefixname + '_bestz.med'
    print(f'{aux.sNOW()}[INFO] Packing {dzi_tmp} to {bestzmed}...')
    packMED = f'{rasar} pack {dzi_tmp} {bestzmed}'
    os.system(packMED)
    print(f'{aux.sNOW()}[INFO] {bestzmed} completed! removing temporary dzi folder...')
    shutil.rmtree(dzi_tmp)
    return

## replace label image with a QR code image
import qrcode

def replaceLabelImageWithQRCode(medfname):
    args = aux.getConfig()
    exe_rasar = args['exe_rasar']
    mpath, mfile = os.path.split(medfname)
    medprefixname = os.path.splitext(mfile)[0]
    dzipath = os.path.join(mpath, 'dzi')
    if not os.path.exists(dzipath):
        os.makedirs(dzipath)
    ## create QR code image
    qrlabel = qrcode.make(medprefixname)
    qrlabel.save(os.path.join(dzipath, 'label.jpg'))
    ## extract all other files from.med file
    with asarlib.AsarFile(medfname) as unpackmed:
        dirwalk = unpackmed.listdir()
        for i, ass in enumerate(dirwalk):
            if '_files' in ass:
                unpackmed.extract(ass, dzipath)
            elif ass != 'label.jpg':
                unpackmed.extract_file(ass, dzipath)
    ## pack .med file
    medfile = f'{mpath}\\{medprefixname}-qrlabel.med'
    packMED = f'{exe_rasar} pack {dzipath} {medfile}'
    os.system(packMED)
    print(f'{aux.sNOW()}[INFO] {os.path.basename(medfile)} completed! removing temporary dzi folder...')
    shutil.rmtree(dzipath)
    return

## crop tile from .med file
os.environ['OPENCV_IO_MAX_IMAGE_PIXELS'] = str(pow(2, 50))
import cv2
import io
import webp
import numpy as np
import math
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

def cropCellFromMEDfile(medfname, x_topleft, y_topleft, fov_size_x, fov_size_y):
    ## read .med file using asarlib
    asar = asarlib.AsarFile(medfname)
    z0tree = asar.listdir('Z0_files')
    ##
    pyramid_bottom_layer = sorted([int(x) for x in z0tree if x.isnumeric()])[-1]
    dzi_path = f'Z0_files/{pyramid_bottom_layer}'
    # use an auxiliary image to cover the ROI, then crop the part we need
    tile_x, tile_y = int(x_topleft // 254), int(y_topleft // 254)
    img_aux_x_tile_num, img_aux_y_tile_num = math.ceil(fov_size_x / 254) + 1, math.ceil(fov_size_y / 254) + 1

    img_aux = np.full((img_aux_y_tile_num * 254, img_aux_x_tile_num * 254, 3), 243, dtype=np.uint8) # 243 = background value (roughly)
    webplist = asar.listdir(dzi_path)
    for x in range(img_aux_x_tile_num):
        for y in range(img_aux_y_tile_num):
            webpname = f'{tile_x + x}_{tile_y + y}.webp'
            img_dzi_path = f"{dzi_path}/{webpname}"
            if webpname in webplist:
                readwebp = asar.read_file(img_dzi_path, decode=False)
                pil_img = Image.open(io.BytesIO(readwebp))
                img_dzi = np.array(pil_img)[1 if tile_y + y > 0 else 0:-1, 1 if tile_x + x > 0 else 0:-1, :]
            else:
                continue
            img_aux[y*254 : min((y+1)*254, y*254+img_dzi.shape[0]), x*254 : min((x+1)*254, x*254+img_dzi.shape[1]), :] = img_dzi
    img = img_aux[y_topleft - tile_y*254:y_topleft - tile_y*254 + fov_size_y, x_topleft - tile_x*254:x_topleft - tile_x*254 + fov_size_x, :]
    ##
    asar.close()
    return img

def cropCellFromLayerOfMEDfile(medfname, whichz, x_topleft, y_topleft, fov_size_x, fov_size_y):
    ## read .med file using asarlib
    asar = asarlib.AsarFile(medfname)
    ztree = asar.listdir(f'Z{whichz}_files')
    ##
    pyramid_bottom_layer = sorted([int(x) for x in ztree if x.isnumeric()])[-1]
    dzi_path = f'Z{whichz}_files/{pyramid_bottom_layer}'
    # use an auxiliary image to cover the ROI, then crop the part we need
    tile_x, tile_y = int(x_topleft // 254), int(y_topleft // 254)
    img_aux_x_tile_num, img_aux_y_tile_num = math.ceil(fov_size_x / 254) + 1, math.ceil(fov_size_y / 254) + 1

    img_aux = np.full((img_aux_y_tile_num * 254, img_aux_x_tile_num * 254, 3), 243, dtype=np.uint8) # 243 = background value (roughly)
    webplist = asar.listdir(dzi_path)
    for x in range(img_aux_x_tile_num):
        for y in range(img_aux_y_tile_num):
            webpname = f'{tile_x + x}_{tile_y + y}.webp'
            img_dzi_path = f"{dzi_path}/{webpname}"
            if webpname in webplist:
                readwebp = asar.read_file(img_dzi_path, decode=False)
                pil_img = Image.open(io.BytesIO(readwebp))
                img_dzi = np.array(pil_img)[1 if tile_y + y > 0 else 0:-1, 1 if tile_x + x > 0 else 0:-1, :]
            else:
                continue
            img_aux[y*254 : min((y+1)*254, y*254+img_dzi.shape[0]), x*254 : min((x+1)*254, x*254+img_dzi.shape[1]), :] = img_dzi
    img = img_aux[y_topleft - tile_y*254:y_topleft - tile_y*254 + fov_size_y, x_topleft - tile_x*254:x_topleft - tile_x*254 + fov_size_x, :]
    ##
    asar.close()
    return img

