# UtilityBOX  
**UtilityBox** A set of tools to collecct/summarize analyzed metadata by AIxMED products (AIxURO. AIxTHY) for analysis and review  
### Model Inference  
command line execute model infernece to specified folder which contains WSI files  
the supported WSI formats are SVS, NDPI, MRXS, TIF/TIFF (partial), DICOM (specified format)  
**[INPUT]**  
`wsifolder`: folder contains WSI files for model inference  
`dcproduct`: model product name, default: AIxURO  
`dcversion`: decart version, default: 2.7.4   
`bmetadata`: default: True, to output inference/analysis metadata to a CSV  
***Example***  
``` python
import runmodel as oo

wsifolder = r'd:\workfolder\testzone'
dcproduct = 'AIxURO'
dcversion = '2.7.4'
bmetadata = True

oo.doModelInference(wsifolder, modelname=dcproduct, decart_version=dcversion, bmetadata=bmetadata)
```
### Collect analysis metadata and save to CSV  
load analysis metadata, summarize the cells count and traits (score large than threshold (0.4 for now))  
**[INPUT]**  
`aixpath`: folder contains .aix files to be summarizing  
`thismpp`: magnification per pixel, default: 0.25  
***Exampe***  
``` python
import runmodel as oo

aixpath = r'E:\metadata\aixthy'
oo.collectAnaysisMetadata(aixpath)
```
### Convert WSI to MED format  
command line to convert WSI (NDPI, MRXS) to MED format  
**[INPUT]**  
`wsifname`: input WSI file name  
`zlayers`: WSI contains how many layers of images  
[note]  
the default bestz layer is the middle layer of zlayers , if multiple layers  
***Example***  
``` python
import imgfuncs as imf

wsifname = r'd:\workfolder'   
imf.convertWSI2MED(wsifname, bestzonly=False)  
```
### Extract single layer from multi-layers .med file   
**[INPUT]**  
`medfname`: multi-layers .med file name  
`dstpath`: destination path to store single layer .med files  
`modelname`: do model inference if modelname != ''    
``` python
import runmodel as oo

whichmed = r'd:\workfolder\medaix\thismed.med'
dstpath = r'd:\workfolder\medaix'

oo.extractSingleLayersFromMultiLayersMED(medfname, dstpath, modelname='')
```
### Batch replace label image to QRcode image from .med files  
**[input]**  
`medpath`: path contains .med files  
``` python
import os, glob
import medfuncs as mf
import auxfuncs as aux

medpath = r'd:\workfolder\medaix'
medlist = []
if os.path.isdir(medpath):
    medlist = glob.glob(os.path.join(medpath, '*.med'))
    if len(medlist) == 0:
        aux.printmsg(f'[ERROR] No .med files found in {medpath}', True)
    else:
        dzipath = os.path.join(medpath, 'dzi')
        if not os.path.isdir(dzipath):
            os.mkdir(dzipath)
elif os.path.isfile(medpath):
    if os.path.splitext(medpath)[1] == '.med':
        dzipath = os.path.join(os.path.splitext(medpath)[0], 'dzi')
        medlist.append(medpath)
    else:
        aux.printmsg(f'[ERROR] {os.path.basename(medpath)} is not a .med file', True)

if len(medlist) > 0:
    if not os.path.isdir(dzipath):
        os.mkdir(dzipath)
    for i in range(len(medlist)):  
        mf.replaceLabelImageWithQRCode(medlist[i])  
    aux.printmsg(f'[INFO] changed to QRcode label for {len(medlist)} .med files ', True)  
```
### Crop tile from multiple layers of .med file, sharpness comparison if needs  
**[INPUT]**    
`medfname`: .med file contains multiple layers of images  
`tile_topleft_x`: x coordinate of top left corner of the tile to be cropped  
`tile_topleft_y`: y coordinate of top left corner of the tile to be cropped  
`tile_width`: width of the tile to be cropped  
`tile_height`: height of the tile to be croped    
***Example***  
``` python
import os
import medfuncs as mf
import aixfuncs as af
import imgfuncs as imf
import auxfuncs as aux

medfname = r'd:\workfolder\crop-tile\C111-14898.med'
medjson = mf.getMetadataFromMED(medfname)
sizeZ = medjson.get('SizeZ', 1)
bestZ = medjson.get('BestFocusLayer', 0)
if sizeZ == 1:
    aux.printmsg(f'[WARNING] Only one layer found in the MED file.', True)
## check whether .aix file exists as well
aixfname = medfname.replace('.med', '.aix')
if os.path.isfile(aixfname):
    meta, catecount, celllist = af.getCellsInfoFromAIX(aixfname)
    print(meta)
    print(catecount)
    print(celllist[0])
else:
    print('No aix file found.')
## create tile folder
tilefolder = os.path.join(os.path.dirname(medfname), f'tiles')
if not os.path.isdir(tilefolder):
    os.mkdir(tilefolder)
for i in range(10):
    tx, ty, tw, th = aux.getCellTilePos(celllist[i]['segments'])
    tilesdir = os.path.join(tilefolder, f'{tx}_{ty}')
    if not os.path.isdir(tilesdir):
        os.mkdir(tilesdir)
    for z in range(sizeZ):
        tile_image = mf.cropCellFromLayerOfMEDfile(medfname, z, tx, ty, tw, th)
        thistile = os.path.join(tilesdir, f'{tx}_{ty}_z{z:02}.png')
        imf.saveCropTile2PNG(tile_image, thistile, z)
    imf.saveMutiPNG2GIF(tilesdir, os.path.join(tilefolder, f'tile_{tx}_{ty}.gif'))
```
***Example***  
*draw multiple cell tiles for comparison*  
``` python
import matplotlib.pyplot as plt

tx, ty, tw, th = aux.getCellTilePos(celllist[1]['segments'])
fsize = (int(tw/10), int(th/10))
fig = plt.figure(figsize=fsize, dpi=144)
for i in range(sizeZ):
    tile_image = mf.cropCellFromLayerOfMEDfile(medfname, i, tx, ty, tw, th)
    ax = plt.subplot(1, sizeZ, i+1)
    ax.imshow(tile_image)
    ax.axis('off')
    ax.set_title(f'z{i}', fontsize=8)
plt.tight_layout(pad=0.05)
plt.show()
```
***Example***  
*Save multipe cell tiles into animation GIF*  
``` python
from PIL import Image, ImageDraw

tx, ty, tw, th = aux.getCellTilePos(celllist[20]['segments'])
tilesdir = r'd:\workfolder\temp'
for z in range(sizeZ):
    tile_image = mf.cropCellFromLayerOfMEDfile(medfname, z, tx, ty, tw, th)
    thistile = os.path.join(tilesdir, f'{tx}_{ty}_z{z:02}.png')
    ##imf.saveCropTile2PNG(tile_image, thistile)
    cropimg = Image.fromarray(tile_image)
    imgw, imgh = cropimg.size
    draw = ImageDraw.Draw(cropimg)
    draw.text((8, imgh-16), f'z{z:02}', (0, 0, 0))
    cropimg.save(os.path.join(tilesdir, f'{tx}_{ty}_z{z:02}.png'))
imf.saveMutiPNG2GIF(tilesdir, os.path.join(tilefolder, f'tile_{tx}_{ty}.gif'))
```

### Analyze metadata of multiple layers of .med/.aix files for cell comparison  
** [INPUT] **   
`aixpath`: folder containing multiple layers of .med/.aix files  
[Note]  
It's better to contain same number of .med files for retrieving med metadata and cropping cell tiles   
***Example***  
``` python
import os, glob
import aixfuncs as af
import medfuncs as mf
import csvfuncs as cf
import auxfuncs as aux

aixpath = r'd:\workfolder\cell-comparison\UCSF002'
# get mpp from med file
medlist = glob.glob(f'{aixpath}\\*.med')
if len(medlist) == 0:
    aux.printmsg(f'[WARNING] {wsifolder} does not contain any .med file, can not get MPP data')
    thismpp = 0.25
else:
    meddata = mf.getMetadataFromMED(medlist[0])
    thismpp = meddata['MPP']
##
cf.processAIXmetadata(aixpath, len(medlist), thismpp)
##
cf.analyzeCellsCoverage(os.path.join(aixpath, 'csvfiles'))
```
