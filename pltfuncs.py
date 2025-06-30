import os, glob
os.environ['OPENCV_IO_MAX_IMAGE_PIXELS'] = str(pow(2, 50))
import cv2
import io
import gzip
import webp
import numpy as np
import math
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs

import auxfuncs as aux
import medfuncs as mf

## this function only for dump trait name in cell comparison
def getCellTraitTagName(whichmodel, modelversion, tagidx):
    if whichmodel == 'AIxURO':
        '''
        traitname = ['hyperchromasia', 'clumpedchromtin', 'irregularmembrane', 'pyknotic',
                 'lightnesseffect', 'dryingartifact', 'degenerated', 'smudged',
                 'unfocused', 'barenucleus', 'binuclei', 'normal',
                 'FibrovascularCore', 'NuclearPlemorphism']
        '''
        traitname = ['HC', 'CC', 'IM', 'PY', 'LE', 'DA', 'DG', 'SM', 'UF', 'BN', 'BI', 'NM', 'FC', 'NP']
    else:   ## 'AIxTHY':
        if modelversion[:6] in ['2025.2']:
            '''
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
            traitname = ['PA', 'CO', 'MF', 'FU', 'NE', 'MG', 'DG', 'NM', 'PI', 'GR', 
                         'MM', 'CC', 'PN', 'PC', 'SP', 'BI', 'SD', 'LE', 'DA', 'UF'] 
        else:
            '''
            traitname = ['microfollicles', 'papillae', 'palenuclei', 'grooving', 'pseudoinclusions',
                         'marginallyplaced', 'plasmacytoid', 'saltandpepper', 'FibrovascularCore', 'NuclearPlemorphism']
            '''
            traitname = ['MF', 'PA', 'PN', 'GV', 'PI', 'MP', 'PL', 'SP', 'FC', 'NP']
    if tagidx >= len(traitname):
        aux.printmsg('[ERROR] can not get trait tag-{tagix} in {whichmodel}')
        return ''
    else:
        return traitname[tagidx]

## crop tile from .med files
def compareSameCellFromLayersOfMED(medpath, cellpos, celltype, celltags, howmany=0, ncratio=[], cellarea=[]):
    pngpath = os.path.join(medpath, 'cells')
    if os.path.isdir(pngpath) == False:
        os.mkdir(pngpath)
    tx, ty, tw, th = cellpos
    tilecmp = os.path.join(pngpath, f'{tx}_{ty}.png')
    if os.path.isfile(tilecmp):      ## cell comparison png already existed
        return tilecmp
    ## check med files
    medlist = glob.glob(f'{medpath}\\*.med')
    if (len(medlist) == 0) or (howmany >0 and len(medlist) < howmany):
        aux.printmsg(f'[WARNING] something wrong, {len(medlist)} .med files in {medpath}')
        return
    medlist.sort()
    num_medfiles = len(medlist)
    nlayers = num_medfiles if howmany == 0 else howmany
    imid = num_medfiles // 2
    if howmany == 0:
        ifrom, ito = 0, num_medfiles
    else:
        ifrom, ito = imid-(howmany//2), imid+(howmany//2)+1
    ## pyplot figure
    fig = plt.figure(figsize=(9, 4), dpi=144)
    gs_inner = gs.GridSpec(3, nlayers, figure=fig, wspace=0.05, hspace=0)
    ## grid 0: draw cell tile
    blurdata = [0 for i in range(nlayers)]
    for i in range(nlayers):
        cropimg = mf.cropCellFromMEDfile(medlist[ifrom+i], tx, ty, tw, th) 
        blurdata[i] = cv2.Laplacian(cropimg, cv2.CV_64F).var()

        axtile = fig.add_subplot(gs_inner[0, i])
        axtile.imshow(cropimg)
        axtile.axis('off')
        axtile.set_title(celltype[ifrom+i], fontsize=7)
    ## grid 1: NC ratio, cell area (AIxURO), and triat tags
    model = 'AIxURO' if ncratio != [] else 'AIxTHY'
    if model == 'AIxTHY':   # temporary
        modelver = '2025.2-0526' if len(celltags) == 20 else '2024.2-0625'
    else:
        modelver = ''
    niltags = [0.0 for i in range(len(celltags))]
    y_txt_pos = 1.0
    for i in range(nlayers):
        if celltags == niltags:
            continue
        axtags = fig.add_subplot(gs_inner[1, i])
        axtags.axis('off')
        if model == 'AIxURO':
            if len(ncratio) > nlayers:
                axtags.text(0.0, y_txt_pos, f'NC%: {ncratio[ifrom+i]}')
                y_txt_pos -= 0.1
            if len(cellarea) > nlayers:
                axtags.text(0.0, y_txt_pos, f'Area: {cellarea[ifrom+i]}')
                y_txt_pos -= 0.1
        for j in range(len(celltags)):
            if celltags[i][j] < 0.4:
                continue
            axtags.text(0.0, y_txt_pos, f'{getCellTraitTagName(model, modelver, j)}: {celltags[i][j]}', fontsize=8)
            y_txt_pos -= 0.1
    ## grid 2: plot sharpness/blurry curve
    xx = range(ifrom+1, ito+1, 1)
    yy = blurdata
    axblur = fig.add_subplot(gs_inner[2, :])
    axblur.xaxis.set_major_locator(plt.MultipleLocator(1))
    axblur.plot(xx, yy,color='gray', linestyle='--', linewidth=0.5, marker='o', markerfacecolor='blue', markersize=8)
    axblur.set_title('Blur Detection (cv2.Laplacian)')

    fig.savefig(tilecmp)
    plt.close(fig)
    aux.printmsg('[INFO] compareSameCellsFromLayersofMED() completed')
    return tilecmp

## plot cell coverage data using Matplotlib
def plotCellsDistribution(csvfname, pngtitle, tcCategories, aspectratio=1.0):
    '''
    tcCategories: those categories of cells to be plotted
    aspectration: image width / height
    '''
    ## preset / prepare data
    colors = {'suspicious':'red', 'atypical':'orange', 'degenerated':'brown', 'benign':'yellow',
              'follicular':'red', 'oncocytic':'orange', 'epithelioid':'brown', 'lymphocytes':'yellow', 
              'histiocytes':'pink', 'colloid':'purple', 'hurthle':'blue'}
    transp = {'suspicious':1.0, 'atypical':0.7, 'degenerated':0.4, 'benign':0.1,
              'follicular':1.0, 'oncocytic':0.8, 'epithelioid':0.8, 'lymphocytes':0.6, 
              'histiocytes':0.6, 'colloid':0.5, 'hurthle':0.4}
    ptsize = {'suspicious':25, 'atypical':25, 'degenerated':20, 'benign':15,
              'follicular':25, 'oncocytic':25, 'epithelioid':20, 'lymphocytes':20, 
              'histiocytes':18, 'colloid':18, 'hurthle':16}
    bTCtypes = [False for _ in range(7)]
    for i in range(len(tcCategories)):
        if tcCategories[i] == 'benign' or tcCategories[i] == 'hurthle':
            bTCtypes[0] = True
        elif tcCategories[i] == 'degenerated' or tcCategories[i] == 'colloid':
            bTCtypes[1] = True
        elif tcCategories[i] == 'atypical' or tcCategories[i] == 'histiocytes':
            bTCtypes[2] = True
        elif tcCategories[i] == 'suspicious' or tcCategories[i] == 'lymphocytes':
            bTCtypes[3] = True
        elif tcCategories[i] == 'epithelioid':
            bTCtypes[4] = True
        elif tcCategories[i] == 'oncocytic':
            bTCtypes[5] = True
        elif tcCategories[i] == 'follicular':
            bTCtypes[6] = True
    workpath = os.path.split(csvfname)[0]
    ## read csv file to pandas dataframe
    df = pd.read_csv(csvfname)
    col_layername = 'layer#' if 'layer#' in df.columns else 'found_layer'
    ## plot 3D scatter
    fig = plt.figure(figsize=(10, 10), dpi=144)
    ax3d = fig.add_subplot(111, projection='3d') 
    for i in range(len(tcCategories)):
        ctypename = tcCategories[i]
        dfcells = df[df['celltype'] == ctypename]
        if bTCtypes[i] and len(dfcells) > 0:
            ax3d.scatter(dfcells['tile_x'].tolist(), dfcells['tile_y'].tolist(), 
                         dfcells[col_layername].tolist(),
                         c=colors[ctypename], s=ptsize[ctypename], 
                         alpha=transp[ctypename], edgecolors='w')
    ax3d.set_xlabel('width', fonesize=8)
    ax3d.set_ylabel('height', fonesize=8)
    ax3d.set_zlabel('layer', fonesize=8)
    plt.title(pngtitle)
    plt.savefig(os.path.join(workpath, f'{pngtitle}_scatter3D.png'))
    plt.close(fig)
    aux.printmsg(f'[INFO] plotCellsDistribution()--scatter3D completed')
    ## plot 2D scatter 
    xsize = int(round(8*aspectratio, 0))
    plt.figure(figsize=(xsize, 8), dpi=144)
    plt.style.use('ggplot')
    plt.grid(True, linestyle='--', alpha=0.4)
    for i in range(len(tcCategories)):
        ctypename = tcCategories[i]
        dfcells = df[df['celltype'] == ctypename]
        if bTCtypes[i] and len(dfcells) > 0:
            plt.scatter(dfcells['tile_x'].tolist(), dfcells['tile_y'].tolist(),
                        c=colors[ctypename], s=ptsize[ctypename],
                        alpha=transp[ctypename], edgecolors='w')
    plt.xlabel('width', fonesize=8)
    plt.ylabel('height', fonesize=8)
    plt.title('Cell Distribution of {pngtitle}')
    plt.savefig(os.path.join(workpath, f'{pngtitle}_cellDistribution.png'))
    plt.close()
    aux.printmsg(f'[INFO] plotCellsDistribution() completed')

def plotBarchartInLayers(workpath, slidename, tcCategories):
    urotype = ['suspicious', 'atypical', 'degenerated', 'benign', 'other']
    thytype = ['follicular', 'oncocytic', 'epithelioid', 'lymphocytes', 'histiocytes', 'colloid', 'hurthle']
    colours = ['red', 'orange', 'brown', 'yellow', 'pink', 'purple', 'blue']

    outpngname = os.path.join(workpath, f'{slidename}_barchart_{tcCategories}.png')
    if os.path.isfile(outpngname):
        return outpngname

