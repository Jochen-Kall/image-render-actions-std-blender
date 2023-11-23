#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \data\obj_modify.py
# Created Date: Friday, August 13th 2021, 8:12:19 am
# Author: Christian Perwass (CR/AEC5)
# <LICENSE id="GPL-3.0">
#
#   Image-Render standard Blender actions module
#   Copyright (C) 2022 Robert Bosch GmbH and its subsidiaries
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#
# </LICENSE>
###

import json
import re

try:
    import _bpy
    import bpy
    import mathutils
    from pathlib import Path
    from anyblend.cls_boundbox import CBoundingBox
    from anyblend import object as anyobj
    from anyblend import ops_object as objops
    from anyblend import collection as anycln
    from anyblend import viewlayer as anyvl
    from anycam import ops as camops
    from anybase import config, convert, path

    # Modifier decorator stuff
    from anybase.dec.cls_paramclass import paramclass, CParamFields
    from catharsys.decs.decorator_ep import EntryPoint
    from catharsys.util.cls_entrypoint_information import CEntrypointInformation

    g_bInBlenderContext = True
except Exception:
    g_bInBlenderContext = False  # don't worry, but don't call anything from here

from anybase import assertion


############################################################################################
def _EnableRender(_objX, _bEnable, bRecursive=True):
    _objX.hide_render = not _bEnable
    if bRecursive:
        for objC in _objX.children:
            _EnableRender(objC, _bEnable, bRecursive=bRecursive)
        # endfor
    # endif


# enddef


############################################################################################
@paramclass
class CEnableParams:
    sDTI: str = (
        CParamFields.HINT(sHint="entry point identification"),
        CParamFields.REQUIRED("/catharsys/blender/modify/object/enable:1.0"),
        CParamFields.DEPRECATED("sType"),
    )    
    xValue:bool = (CParamFields.REQUIRED(), 
                   CParamFields.HINT(sHint="Enable/Disable Object in all renders"))
# endclass


# -------------------------------------------------------------------------------------------
@EntryPoint(
    CEntrypointInformation.EEntryType.MODIFIER,
    clsInterfaceDoc=CEnableParams,
)

def Enable(_objX, _dicMod, **kwargs):
    assertion.IsTrue(g_bInBlenderContext)
    config.AssertConfigType(_dicMod, "/catharsys/blender/modify/object/enable:1.0")

    mp = CEnableParams(_dicMod)
    # sModType = convert.DictElementToString(
    #     _dicMod,
    #     "sType",
    #     sDefault=convert.DictElementToString(_dicMod, "sDTI", bDoRaise=False),
    # )

    # bEnable = convert.DictElementToBool(_dicMod, "xValue")
    bEnable = mp.xValue
    _EnableRender(_objX, bEnable, bRecursive=True)


# enddef


############################################################################################
@paramclass
class CEnableIfBoundBoxParams:
    sDTI: str = (
        CParamFields.HINT(sHint="entry point identification"),
        CParamFields.REQUIRED("/catharsys/blender/modify/object/enable-if/bound-box:1.0"),
        CParamFields.DEPRECATED("sType"),
    )    
    xValue:bool = (CParamFields.REQUIRED(), 
                   CParamFields.HINT(sHint="Enable/Disable Object in all renders"))
    sTarget:str = (
        CParamFields.REQUIRED(),
        CParamFields.HINT(sHint="The name of the target object, whose bounding box will be used.")
    )
    bCompoundTarget:bool = (
        CParamFields.HINT(sHint="""If set to true, the bounding box is evaluated for the object sTarget and all its' children.
                If set to false, only the mesh of sTarget itself without children is used."""),
        CParamFields.DEFAULT(False)
    )
    fBorder:bool = (
        CParamFields.HINT(sHint="""Size of border around target object's bounding box."""),
        CParamFields.DEFAULT(0.0)
    )
    sRelation:str = (
        CParamFields.HINT(sHint="""The relation to test."""),
        CParamFields.OPTIONS(["INSIDE", "OUTSIDE", "INTERSECT"], xDefault="INSIDE")
    )

# endclass


# -------------------------------------------------------------------------------------------
@EntryPoint(
    CEntrypointInformation.EEntryType.MODIFIER,
    clsInterfaceDoc=CEnableIfBoundBoxParams,
)
def EnableIfBoundBox(_objX, _dicMod, **kwargs):
    """Enable/disable object depending on its' relation to a target object's bounding box.

    Parameters
    ----------
    _objX : Blender object
        The object
    _dicMod : dict
        Arguments

    Configuration Parameters
    -----------------------
    sTarget: string
        The name of the target object, whose bounding box will be used.
    bCompoundTarget: bool, optional
        If set to true, the bounding box is evaluated for the object sTarget and all its' children.
        If set to false, only the mesh of sTarget itself without children is used.
    fBorder: float, optional
        Size of border around target object's bounding box. Default is 0.0.
    sRelation: string, optional
        The relation to test. Must be one of ["INSIDE", "OUTSIDE", "INTERSECT"]. Default is "INSIDE".
    """
    assertion.IsTrue(g_bInBlenderContext)
    config.AssertConfigType(_dicMod, "/catharsys/blender/modify/object/enable-if/bound-box:1.0")

    mp = CEnableIfBoundBoxParams
    # fBorder = convert.DictElementToFloat(_dicMod, "fBorder", fDefault=0.0)
    # sRelation = convert.DictElementToString(_dicMod, "sRelation", sDefault="INSIDE").upper()
    # sTarget = convert.DictElementToString(_dicMod, "sTarget")
    # bCompoundTarget = convert.DictElementToBool(_dicMod, "bCompoundTarget", bDefault=False)

    objTarget = bpy.data.objects.get(mp.sTarget)
    if objTarget is None:
        raise RuntimeError(f"Target object '{mp.sTarget}' not found")
    # endif

    boxTarget = CBoundingBox(_objX=objTarget, _bCompoundObject=mp.bCompoundTarget, _bUseMesh=True)

    bEnable = None
    match mp.sRelation:
        case "INSIDE":
            bEnable = boxTarget.IsObjectInside(_objX, _fBorder=mp.fBorder)

        case "OUTSIDE":
            bEnable = boxTarget.IsObjectOutside(_objX, _fBorder=mp.fBorder)

        case "INTERSECT":
            bEnable = boxTarget.IsObjectIntersect(_objX, _fBorder=mp.fBorder)

    # endmatch

    if bEnable is None:
        raise RuntimeError(f"Unsupported relation '{mp.sRelation}'. Expect one of ['INSIDE', 'OUTSIDE', 'INTERSECT']")
    # endif

    anyobj.Hide(_objX, bHide=not bEnable, bHideRender=not bEnable, bRecursive=True)

    # sName = f"{objTarget.name}.BoundBox"
    # if sName not in bpy.data.objects:
    #     xCln = anycln.FindCollectionOfObject(bpy.context, objTarget)
    #     print(f"boxTarget '{objTarget.name}': {boxTarget.lCorners}")

    #     boxTarget.CreateBlenderObject(_sName=sName, _xCollection=xCln)
    # # endif


# enddef


############################################################################################
@paramclass
class CModifyPropertiesParams:
    sDTI: str = (
        CParamFields.HINT(sHint="entry point identification"),
        CParamFields.REQUIRED("/catharsys/blender/modify/object/properties:1.0"),
        CParamFields.DEPRECATED("sType"),
    )    
    mValues:dict = (CParamFields.REQUIRED(), 
                   CParamFields.HINT(sHint="Attributes to be modified"))

# endclass


# -------------------------------------------------------------------------------------------
@EntryPoint(
    CEntrypointInformation.EEntryType.MODIFIER,
    clsInterfaceDoc=CModifyPropertiesParams,
)

def ModifyProperties(_objX, _dicMod, **kwargs):
    """Modify attributes of a blender object
    Modify custom properties of an object.

    Parameters
    ----------
    _objX : blender object
        Object to be modified
    _dicMod : dict
        Attributes to be modified

    Raises
    ------
    Exception
        Raise an exception if anything fails during modification of the object

    """
    assertion.IsTrue(g_bInBlenderContext)

    mp = CModifyPropertiesParams(_dicMod)
 
    if not isinstance(mp.dicValues, dict):
        raise RuntimeError("Missing element 'mValues' in modify properties modifier")
    # endif

    for sKey, xValue in mp.dicValues.items():
        if not isinstance(sKey, str):
            raise RuntimeError("Invalid key type in modify attributes: {}".format(sKey))
        # endif

        if sKey not in _objX:
            raise RuntimeError(f"Property '{sKey}' not found in object '{_objX.name}'")
        # endif

        if isinstance(xValue, int) or isinstance(xValue, float) or isinstance(xValue, str):
            _objX[sKey] = xValue

        else:
            sType = convert.ToTypename(xValue)
            raise RuntimeError(f"Value for property '{sKey}' of unsupported type '{sType}'")
        # endif

    # endfor

    # Need to tag the object for updates,
    # so that drivers depending on the properties
    # are updated. Note that a driver update
    # can only be triggered by changing the
    # current scene frame, it seems.
    # You can use anyblend.scene.UpdateDrivers() for this.
    _objX.update_tag()


# enddef


############################################################################################
@paramclass
class CModifyAttributesParams:
    sDTI: str = (
        CParamFields.HINT(sHint="entry point identification"),
        CParamFields.REQUIRED("/catharsys/blender/modify/object/attributes:1.0"),
        CParamFields.DEPRECATED("sType"),
    )    
    mValues:dict = (CParamFields.REQUIRED(), 
                   CParamFields.HINT(sHint="Attributes to be modified"),
                   CParamFields.DEPRECATED("dValues")
                   )

# endclass


# -------------------------------------------------------------------------------------------
@EntryPoint(
    CEntrypointInformation.EEntryType.MODIFIER,
    clsInterfaceDoc=CModifyAttributesParams,
)

def ModifyAttributes(_objX, _dicMod, **kwargs):
    """Modify attributes of a blender object
    For each parameter in _dicMod, create a command to modify the object attributes.

    Parameters
    ----------
    _objX : blender object
        Object to be modified
    _dicMod : dict
        Attributes to be modified

    Raises
    ------
    Exception
        Raise an exception if anything fails during modification of the object

    """

    mp = CModifyAttributesParams(_dicMod)

    assertion.IsTrue(g_bInBlenderContext)

    # "dValues" tag is deprecated
    # dicValues = _dicMod.get("mValues", _dicMod.get("dValues"))
    dicValues = mp.mValues
    if not isinstance(dicValues, dict):
        raise RuntimeError("Missing element 'mValues' in modify attributes modifier")
    # endif

    for sKey, xValue in dicValues.items():
        if not isinstance(sKey, str):
            raise RuntimeError("Invalid key type in modify attributes: {}".format(sKey))
        # endif

        lKey = sKey.split(".")
        objY = _objX
        sFinalKey = None
        lPath = [_objX.name]

        for iIdx, sSubKey in enumerate(lKey):
            if not hasattr(objY, sSubKey):
                raise RuntimeError("Object '{}' has no attribute '{}'".format(".".join(lPath), sSubKey))
            # endif

            if iIdx >= len(lKey) - 1:
                sFinalKey = sSubKey
                break
            # endif

            lPath.append(sSubKey)
            objY = getattr(objY, sSubKey)
        # endfor

        try:
            setattr(objY, sFinalKey, xValue)
        except Exception:
            raise Exception(
                "Could not set attribute '{}' of object '{}' to value: {} ".format(sKey, _objX.name, str(xValue))
            )
        # endtry
    # endfor


# enddef


################################################################################
@paramclass
class CParentToObjectParams:
    sDTI: str = (
        CParamFields.HINT(sHint="entry point identification"),
        CParamFields.REQUIRED("/catharsys/blender/modify/object/parent:1.0"),
        CParamFields.DEPRECATED("sType"),
    )    
    sParentObject:str = (CParamFields.REQUIRED(), 
                         CParamFields.HINT(sHint="The name of the object to parent objX to."))
    bKeepTransform: bool =(CParamFields.DEFAULT(False),
                           CParamFields.HINT(sHint="Whether to keep the current absolute position of an object after parenting, or not."))
    bSkipNonexistingParent: bool = (CParamFields.DEFAULT(False),
                                    CParamFields.HINT(sHint="""Control how non existing parent target is handled. 
                                        If set to true, modifier skips,
                                        if set to false an error is thrown. Default behavior is throwing an error"""))
# endclass


# -------------------------------------------------------------------------------------------
@EntryPoint(
    CEntrypointInformation.EEntryType.MODIFIER,
    clsInterfaceDoc=CParentToObjectParams,
)
def ParentToObject(_objX, _dicMod, **kwargs):
    """Parent object to another

    Args:
        _objX (bpy.types.Object): The object that is parented to a given object
        _dicMod (dict): A dictionary of placement parameters.

    Configuration Args:
        sParentObject (str): The name of the object to parent objX to.
        bKeepTransform (bool): Whether to keep the current absolute position of an object after parenting, or not.
        bSkipNonexistingParent (bool, optional) : Control how non existing parent target is handled. If set to true, modifier skips,
                        if set to false an error is thrown. Default behavior is throwing an error.
    """
    # instantiate modifier parameter class
    mp = CParentToObjectParams(_dicMod)

    if _objX.type == "CAMERA":
        camops.ParentAnyCam(sCamId=_objX.name, sParentId=mp.sParentObject)

    else:
        objParent = bpy.data.objects.get(mp.sParentObject)
        if objParent is None:
            if not mp.bSkipNonexistingParent:
                raise RuntimeError(f"Object '{mp.sParentObject}' not found for parenting")
            # endif
        else:
            anyobj.ParentObject(objParent, _objX, bKeepTransform=mp.bKeepTransform)
        # endif
    # endif

    anyvl.Update()


# enddef


################################################################################
@paramclass
class CRenameObjectParams:
    sDTI: str = (
        CParamFields.HINT(sHint="entry point identification"),
        CParamFields.REQUIRED("/catharsys/blender/modify/object/rename:1.0"),
        CParamFields.DEPRECATED("sType"),
    )
    sReplace: str = (
        CParamFields.REQUIRED(),
        CParamFields.HINT(sHint=""" The new object name. If bUseRegEx == true, this is expected to be a
            regular expression, that can use the capture groups of the search term
            to create the new name.""")
    )
    bUseRegEx:bool = (
        CParamFields.DEFAULT(False),
        CParamFields.HINT(sHint="""Determines whether a regular expression is used for renaming or not.
            The argument 'sSearch' is only used, if this argument is true.
            This modifier uses the python function 're.sub()'. See its' documentation
            for more information on how to use capture groups:
                https://docs.python.org/3/library/re.html"""),
        CParamFields.DEPRECATED("sUseRegEx")
    )
    sSearch: str = (
        CParamFields.DEFAULT(""),
        CParamFields.HINT(sHint="""The regular expression search string used for regular expression replacement.
            Should define capture groups for replacement.""")
    )
# endclass


# -------------------------------------------------------------------------------------------
@EntryPoint(
    CEntrypointInformation.EEntryType.MODIFIER,
    clsInterfaceDoc=CRenameObjectParams,
)
def RenameObject(_objX, _dicMod, **kwargs):
    """Rename object with regular expression

    Args:
        _objX (bpy.types.Object): The object that is parented to a given object
        _dicMod (dict): A dictionary of placement parameters.

    Configuration Args:
        sReplace (str):
            The new object name. If bUseRegEx == true, this is expected to be a
            regular expression, that can use the capture groups of the search term
            to create the new name.

        bUseRegEx (bool, optional, default=False):
            Determines whether a regular expression is used for renaming or not.
            The argument 'sSearch' is only used, if this argument is true.
            This modifier uses the python function 're.sub()'. See its' documentation
            for more information on how to use capture groups:
                https://docs.python.org/3/library/re.html

        sSearch (str, required if bUseRegEx == true):
            The regular expression search string used for regular expression replacement.
            Should define capture groups for replacement.
    """

    mp=CRenameObjectParams(_dicMod)
    sName = _objX.name

    sReplace = mp.sReplace
    # sReplace = convert.DictElementToString(_dicMod, "sReplace")
    if sReplace is None:
        raise RuntimeError("Element 'sReplace' not given in object rename modifier")
    # endif

    bUseRegEx = mp.bUseRegEx
    # bUseRegEx = convert.DictElementToBool(_dicMod, "sUseRegEx", bDefault=False)

    sNewName = None
    if bUseRegEx:
        sSearch = mp.sSearch
        # sSearch = convert.DictElementToString(_dicMod, "sSearch")
        if sSearch is None:
            raise RuntimeError("Element 'sSearch' not given in object rename modifier")
        # endif

        sNewName = re.sub(sSearch, sReplace, sName)
    else:
        sNewName = sReplace
    # endif

    _objX.name = sNewName


# enddef


################################################################################
@paramclass
class CLogObjectParams:
    sDTI: str = (
        CParamFields.HINT(sHint="entry point identification"),
        CParamFields.REQUIRED("/catharsys/blender/modify/object/log:1.0"),
        CParamFields.DEPRECATED("sType"),
    )    
    lAttributes: list = (
        CParamFields.REQUIRED(list[str]), 
        CParamFields.HINT(sHint="List of names of attributes that shall be logged")
        )
    sLogFile: str = (
        CParamFields.REQUIRED(),
        CParamFields.HINT(sHint = """The filename of the json file to be written. If not given
            or None, the attributes will be logged to the console.""")
    )
# endclass


# -------------------------------------------------------------------------------------------
@EntryPoint(
    CEntrypointInformation.EEntryType.MODIFIER,
    clsInterfaceDoc=CLogObjectParams,
)

def LogObject(_objX, _dicMod, **kwargs):
    """Log object attributes to json file

    Args:
        _objX (bpy.types.Object): The object that shall be logged
        _dicMod (dict): A dictionary of logging parameters

    Configuration Args:
        lAttributes (list):
            List of names of attributes that shall be logged

        sLogFile (str):
            The filename of the json file to be written. If not given
            or None, the attributes will be logged to the console.
    """
    mp = CLogObjectParams
    # lAttributes = _dicMod.get("lAttributes")

    if mp.lAttributes is None:
        raise RuntimeError("List of object attribute names not given")
    # endif

    # sLogFile = _dicMod.get("sLogFile")

    dicJson = {}

    for sAttr in mp.lAttributes:
        # some objects do not support setting an attribute via setattr
        # but by []
        # this is handled here

        if sAttr in _objX:
            xAttribute = _objX[sAttr]
        elif hasattr(_objX, sAttr):
            xAttribute = getattr(_objX, sAttr)
        else:
            raise KeyError(f"Attribute {sAttr} not in {_objX.name}")
        # endif

        # it is assumed that xAttribute is a json parsable string like object,
        # in which case it will be converted to the respective python object
        # if this assumption does not hold, xAttribute will be directly used
        try:
            dicJson[sAttr] = json.loads(xAttribute)
        except:
            dicJson[sAttr] = xAttribute
        # end try
    # endfor

    if mp.sLogFile is not None:
        print("=== Logging", _objX.name, " to file", mp.sLogFile, "===")

        def default_serializer(_obj):
            return str(_obj)

        with open(mp.sLogFile, "w") as file:
            json.dump(dicJson, file, indent=4, default=default_serializer)
        # endwith
    else:
        print("=== Logging", _objX.name, "===")
        print(dicJson)
    # endif


# enddef


################################################################################
@paramclass
class CExportObjectObjParams:
    sDTI: str = (
        CParamFields.HINT(sHint="entry point identification"),
        CParamFields.REQUIRED("/catharsys/blender/modify/object/export/obj:1.0"),
        CParamFields.DEPRECATED("sType"),
    )    
    sFilePath: str = (
        CParamFields.REQUIRED(), 
        CParamFields.HINT(sHint="Path to export to")
        )
    bCreatePath: bool = (
        CParamFields.HINT(sHint = """ Create Folder if it does not exist."""),
        CParamFields.DEFAULT(False)
    )
# endclass


# -------------------------------------------------------------------------------------------
@EntryPoint(
    CEntrypointInformation.EEntryType.MODIFIER,
    clsInterfaceDoc=CExportObjectObjParams,
)

def ExportObjectObj(_objX, _dicMod, **kwargs):
    mp = CExportObjectObjParams(_dicMod)

    pathFile = path.MakeNormPath(mp.sFilePath)

    if not pathFile.is_absolute():
        pathBlend = Path(bpy.path.abspath("//"))
        pathFile = path.MakeNormPath(pathBlend / pathFile)
    # endif

    if not pathFile.parent.exists() and mp.bCreatePath is True:
        pathFile.parent.mkdir(parents=True, exist_ok=True)
    # endif

    if not pathFile.parent.exists():
        raise RuntimeError(f"Export path for object ' {_objX.name}' does not exist: {(pathFile.parent.as_posix())}")
    # endif

    objops.ExportFromScene_Obj(pathFile, _objX)


# enddef
