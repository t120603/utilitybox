import os, shutil
'''  in case, unable to import pyvips
add_dll_dir = getattr(os, "add_dll_directory", None)
vipsbin = 'c:\\bin\\vips-dev-8.16\\bin'
if callable(add_dll_dir):
    add_dll_dir(vipsbin)
else:
    os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
'''
import pyvips
import openslide
import tifffile
import numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
import cv2
import re
import json
import qrcode
import glob
import auxfuncs as aux

def isNumeric(unknown):
    pattern = r'^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$'
    return bool(re.match(pattern, unknown))

def extractICCandLableImage_openslide(wsipath, dzipath):
    wsi_openslide = openslide.open_slide(wsipath)
    # Get associated images (returns a dictionary)
    associated_images = wsi_openslide.associated_images
    # Access each associated image
    labelNG = True
    for name, image in associated_images.items():
        if name == 'label':
            labelpng = associated_images['label']
            labeljpg = labelpng.convert('RGB')
            labeljpg.save(f'{dzipath}\\label.jpg', 'JPEG')
            labelNG = False
            break
    if labelNG:
        sfilename = os.path.splitext(os.path.basename(wsipath))[0]
        qrlabel = qrcode.make(sfilename)
        qrlabel.save(f'{dzipath}\\label.jpg')
    ## icc profile by openslide
    icc_profile = wsi_openslide.properties.get('openslide.icc-profile')
    if icc_profile:
        with open(f'{dzipath}\\profile.icc', 'wb') as ficc:
            ficc.write(icc_profile)
        iccName = ''        ## ??
        iccSize = len(icc_profile)
    else:
        iccName, iccSize = '', 0
    return wsi_openslide, iccName, iccSize 

def howmanyLayersInNDPI(ndpipath):
    try:
        with tifffile.TiffFile(ndpipath) as wsi:
            count = 0
            nWSIwidth = wsi.pages[0].tags['ImageWidth'].value
            nWSIheight = wsi.pages[0].tags['ImageLength'].value

            for i in range(len(wsi.pages)):
                pagew = wsi.pages[i].tags['ImageWidth'].value if ('ImageWidth' in wsi.pages[i].tags) else 0
                pageh = wsi.pages[i].tags['ImageLength'].value if ('ImageLength' in wsi.pages[i].tags) else 0
                if (pagew == nWSIwidth) and (pageh == nWSIheight):
                    count += 1
            nLayers = count
    except:
        aux.printmsg(f'[ERROR] can not get attributes from {os.path.basename(ndpipath)}', True)
        nLayers = None
    return nLayers

def getNDPIproperties(ndpipath, bestzonly, ndpi, iccname, iccsize):
    ## metadata from openslide.properties
    ndpiPropItems = {'openslide.mpp-x':'MPP', 'openslide.objective-power':'MAG', 'openslide.vendor':'Scanner', 
                    'hamamatsu.Product': 'Product', 'hamamatsu.SourceLens': 'SourceLens',
                    'hamamatsu.Created': 'Created', 'hamamatsu.Updated': 'Updated',
                    'hamamatsu.XOffsetFromSlideCentre': 'XOffsetFromSlideCentre', 'hamamatsu.YOffsetFromSlideCentre': 'YOffsetFromSlideCentre',
                    'tiff.DataTime': 'DataTime', 'tiff.Make': 'Make', 'tiff.Model': 'ScannerModel',
                    'tiff.ResolutionUnit': 'ResolutionUnit', 'tiff.XResolution': 'XResolution',
                    'tiff.Software': 'ScannerSoftware', 'tiff.YResolution': 'YResolution',
                }
    metadict = {}
    metadict['Width'], metadict['Height'] = ndpi.dimensions
    mprop = dict(ndpi.properties)
    for i, k in enumerate(ndpiPropItems):
        read_data = mprop.get(k)
        if read_data != None:
            if isNumeric(read_data):
                if '.' in read_data:
                    thisnum = float(read_data)
                else:
                    thisnum = int(read_data)
                metadict[ndpiPropItems[k]] = thisnum
            else:
                metadict[ndpiPropItems[k]] = read_data
    ## get zstack
    z_layers = howmanyLayersInNDPI(ndpipath)
    if bestzonly or (read_data == None):
        metadict['SizeZ'] = 1
        metadict['LevelCount'] = 1
    else:
        metadict['SizeZ'] = z_layers
        metadict['LevelCount'] = z_layers
        metadict['IndexZ'] = [i+1 for i in range(z_layers)]
        metadict['BestFocusLayer'] = z_layers // 2
    args = aux.getConfig()
    metadict['DeCart'] = args['decart_ver']
    if iccsize != 0:
        metadict['IccProfile'] = iccname
        metadict['IccSize' ] = iccsize
    ## other metadata from pyvips.get_fields()
    mvips = pyvips.Image.new_from_file(ndpipath, access='sequential')
    for tagname in mvips.get_fields():
        if tagname in ['format', 'interpolation', 'xoffset', 'yoffset']:
            metadict[tagname.title()] = mvips.get(tagname)

    sorteddict =  dict(sorted(metadict.items(), key=lambda x:x[0]))
    return sorteddict, z_layers, mvips

def getMRXSproperties(mrxspath, bestzonly, mrxs, iccname, iccsize):
    ## metadata from openslide.properties
    mrxsPropItems = {'openslide.background-color': 'BackgroundColor', 'openslide.bounds-height':'BoundsHeight', 
                 'openslide.bounds-width':'BoundsWidth', 'openslide.bounds-x':'BoundsX', 'openslide.bounds-y':'Bounds-y',
                 'openslide.mpp-x':'MPP', 'openslide.objective-power':'MAG', 'openslide.vendor':'Scanner',
                 'mirax.GENERAL.ADAPTER_SIZE':'ApapterSize', 'mirax.GENERAL.CameraImageDivisionsPerSide':'CameraImageDivisionsPerSide',
                 'mirax.GENERAL.CAMERA_TYPE':'CameraType', 'mirax.GENERAL.COMPRESSED':'Compressed', 'mirax.GENERAL.COMPRESSION': 'Compression',
                 'mirax.GENERAL.COMPRESSION_FACTOR': 'CompressionType', 'mirax.GENERAL.CONFOCAL':'Confocal',
                 'mirax.GENERAL.CURRENT_SLIDE_VERSION':'CurrentSlideVersion', 'mirax.GENERAL.DiskPosition':'DiskPosition',
                 'mirax.GENERAL.EXTENDED_FOCUS_ALGORITHM':'ExtendedFocusAlgorithm', 'mirax.GENERAL.FLAT_FIELD_CORRECTION':'FlatFieldCorrection',
                 'mirax.GENERAL.FOCUS_LIMIT':'FocusLimit', 'mirax.GENERAL.FOCUS_LIMIT_LO':'FocusLimitLo',
                 'mirax.GENERAL.FOCUS_LIMIT_UP':'FocusLimitUp', 'mirax.GENERAL.FOCUS_MAP':'FocusMap',
                 'mirax.GENERAL.IMAGENUMBER_X':'ImagenumberX', 'mirax.GENERAL.IMAGENUMBER_Y':'ImagenumberY', 
                 'mirax.GENERAL.IMAGE_OVERLAP_MICROMETER_X':'ImageOverlapMicrometerX', 'mirax.GENERAL.IMAGE_OVERLAP_MICROMETER_Y':'ImageOverlapMicrometerY', 
                 'mirax.GENERAL.OBJECTIVE_MAGNIFICATION':'ObjectiveMagnification', 'mirax.GENERAL.OBJECTIVE_NAME':'ObjectiveName',
                 'mirax.GENERAL.OPTOVAR_SIZE':'OptovarSize', 'mirax.GENERAL.OUTPUT_RESOLUTION': 'OutputResolution',
                 'mirax.GENERAL.SLIDE_CONTENT':'SlideContent', 'mirax.GENERAL.SLIDE_CREATION_FINISHED':'SlideCreationFinished',
                 'mirax.GENERAL.CREATIONDATETIME':'SlideCreationdatetime', 'mirax.GENERAL.SLIDE_ID':'SlideId', 
                 'mirax.GENERAL.SLIDE_IS_DOUBLE_WIDE':'SlideIsDoubleWide', 'mirax.GENERAL.SLIDE_NAME':'SlideName',
                 'mirax.GENERAL.SLIDE_POSITION_X':'SlidePositionX', 'mirax.GENERAL.SLIDE_POSITION_Y':'SlidePositionY', 
                 'mirax.GENERAL.SLIDE_TYPE':'SlideType', 'mirax.GENERAL.SLIDE_UTC_CREATIONDATETIME':'SlideUtcCreationdatatime', 
                 'mirax.GENERAL.SLIDE_VERSION':'SlideVersion', 'mirax.GENERAL.VIMSLIDE_CAMERA_REAL_BITDEPTH':'VimslideCameraRealBitdepth',
                 'mixax.GENERAL.SLIDE_BITDEPTH':'SlideBitdepth',
                }

    metadict = {}
    #mrxs = openslide.open_slide(mrxspath)
    metadict['Width'], metadict['Height'] = mrxs.dimensions
    mprop = dict(mrxs.properties)
    for i, k in enumerate(mrxsPropItems):
        read_data = mprop.get(k)
        if read_data != None:
            if isNumeric(read_data):
                if '.' in read_data:
                    thisnum = float(read_data)
                else:
                    thisnum = int(read_data)
                metadict[mrxsPropItems[k]] = thisnum
            else:
                metadict[mrxsPropItems[k]] = read_data
    ## get zstack
    read_data = mprop.get('mirax.LAYER_2_LEVEL_0_SECTION.ZSTACK_STEP_COUNT')
    z_layers = int(read_data)
    if bestzonly or (read_data == None):
        metadict['SizeZ'] = 1
        metadict['LevelCount'] = 1
    else:
        metadict['SizeZ'] = z_layers
        metadict['LevelCount'] = z_layers
        metadict['IndexZ'] = [i+1 for i in range(z_layers)]
        metadict['BestFocusLayer'] = z_layers // 2
    args = aux.getConfig()
    metadict['DeCart'] = args['decart_ver']
    if iccsize != 0:
        metadict['IccProfile'] = iccname
        metadict['IccSize' ] = iccsize
    ## other metadata from pyvips.get_fields()
    mvips = pyvips.Image.new_from_file(mrxspath, access='sequential')
    for tagname in mvips.get_fields():
        if tagname in ['format', 'interpolation', 'xoffset', 'yoffset']:
            metadict[tagname.title()] = mvips.get(tagname)

    sorteddict =  dict(sorted(metadict.items(), key=lambda x:x[0]))
    return sorteddict, z_layers, mvips

def convertWSI2MED(wsifname, bestzonly=False):
    args = aux.getConfig()
    exevips = args['exe_vips']
    exeasar = args['exe_rasar']
    dzipath = os.path.join(args['tempzone'], 'dzi')
    if os.path.isdir(dzipath) == False:
        os.mkdir(dzipath)
    wsiformat = os.path.splitext(wsifname)[1][1:].lower()
    if wsiformat in ['mrxs', 'ndpi']:
        aux.printmsg(f'[INFO] start converting {os.path.basename(wsifname)} to .med file', True)
        ## extract label image and icc profile
        props, iccname, iccsize = extractICCandLableImage_openslide(wsifname, dzipath)
        ## create metadata.json
        if wsiformat == 'ndpi':
            dictmeta, zlayers, wsi_pyvips = getNDPIproperties(wsifname, bestzonly, props, iccname, iccsize)
        else:
            dictmeta, zlayers, wsi_pyvips = getMRXSproperties(wsifname, bestzonly, props, iccname, iccsize)
        ## save to dzi\metadata.json
        with open(f'{dzipath}\\metadata.json', 'w') as mjson:
            json.dump(dictmeta, mjson)
        ## command line 'vips dzsave ....'
        if bestzonly:
            bestz = zlayers // 2
            vips_cmd = f'{exevips} dzsave {wsifname}[level={bestz+1},autocrop=true] {dzipath}\\Z0.dz --suffix=.webp --container=fs'
            os.system(vips_cmd)
        else:
            for i in range(zlayers):
                vips_cmd = f'{exevips} dzsave {wsifname}[level={i+1},autocrop=true] {dzipath}\\Z{i}.dz --suffix=.webp --container=fs'
                os.system(vips_cmd)
        ## pack dzi folder to .med
        wsiname = os.path.splitext(os.path.basename(wsifname))[0]
        if bestzonly:
            wsiname = wsiname+'_bestz'
        asar_cmd = f'{exeasar} pack {dzipath} {os.path.dirname(wsifname)}\\{wsiname}.med'
        os.system(asar_cmd)
        ## remove dzi folder
        shutil.rmtree(dzipath)
    else:
        aux.printmsg('[WARNING] currently, only support converting NDPI/MRXS --> MED', True)

def readTIFFtags(wsifname):
    taglist = []
    with tifffile.TiffFile(wsifname) as wsi:
        for i in range(len(wsi.pages)):
            tiftags = {}
            for tag in wsi.pages[i].tags.values():
                tiftags[tag.name] = tag.value
            taglist.append(tiftags)
    return taglist

def loadImage(imgpath):
    img = cv2.imread(imgpath)
    if img is None:
        aux.printmsg(f'[WARNING] cannot load image {imgpath}', True)
        return None
    return img

def saveImage2png(pngfname, pngimage):
    cv2.imwrite(pngfname, pngimage)

def cvt2GrayImage(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def cropTileFromImage(image, tx, ty, tw, th):
    return image[ty:ty+th, tx:tx+tw]        ## note: y first, then x

def calcTileSharpnessValue(grayimg, method='brenner'):
    if method == 'brenner':
        sharpess = 0
        shapes = np.shape(grayimg)
        for x in range(0, shapes[0]-2):
            for y in range(0, shapes[1]):
                sharpness += (int(grayimg[x+2], y)-int(grayimg[x, y]))**2
    elif method == 'laplacian':
        laplacian = cv2.Laplacian(grayimg, cv2.CV_64F)
        sharpness = np.mean(np.abs(laplacian))
    return sharpness

def updateGamma2Image(pngfile, gamma=1.0):
    pngimg = cv2.imread(pngfile)
    ## build a lookup table mapping the pixel values [0, 255] to adjust gamma values
    newGamma = 1.0 / gamma
    lookup_table = np.array([((i/255.0)**newGamma)*255 for i in np.arange(0,256)]).astype('uint8')
    ## apply gamma correction using the lookup table
    return cv2.LUT(pngimg, lookup_table)

def saveCropTile2PNG(cropimg, pngfile, z):
    thisimg = Image.fromarray(cropimg)
    imgw, imgh = thisimg.size
    draw = ImageDraw.Draw(thisimg)
    draw.text((8, imgh-16), f'z{z:02}', (0, 0, 0))
    thisimg.save(pngfile)

def saveMutiPNG2GIF(pngfolder, gifname):
    pnglist = sorted(glob.glob(os.path.join(pngfolder, '*.png')))
    if len(pnglist) == 0:
        print('No png files found.')
        return
    # Create the frames
    frames = []
    for i in pnglist:
        new_frame = Image.open(i)
        frames.append(new_frame)
    # Save into a GIF file that loops forever
    frames[0].save(gifname, format='GIF',
               append_images=frames[1:],
               save_all=True,
               duration=500, loop=0)




