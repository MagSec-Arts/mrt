import maya.cmds as cmds
import mrt_functions as mfunc
import mrt_objects as objects
import maya.mel as mel
import math, os
from functools import partial

class MRT_Module(object):
    def __init__(self, moduleInfo):
        """ Initial class variables."""
        # Module type.
        self.moduleName = moduleInfo['node_type']
        # Number of nodes in the module.
        self.numNodes = moduleInfo['num_nodes']
        # Length of the module.
        self.moduleLen = moduleInfo['module_length']
        # Creation plane.
        self.onPlane = moduleInfo['creation_plane'][-2:]
        # Offset from origin.
        self.moduleOffset = moduleInfo['module_offset']
        # Node Axes.
        self.nodeAxes = moduleInfo['node_axes']
        # Proxy geometry creation on/off.
        self.proxyGeoStatus = moduleInfo['node_compnts'][2]
        # Proxy bones.
        self.proxyGeoBones = moduleInfo['proxy_geo_options'][0]
        # Proxy elbow.
        self.proxyGeoElbow = moduleInfo['proxy_geo_options'][1]

        self.proxyElbowType = moduleInfo['proxy_geo_options'][2]
        # Mirror instance for proxy geometry.
        self.proxyGeoMirrorInstance = moduleInfo['proxy_geo_options'][3]
        # Create mirror module on/off.
        self.mirrorModule = moduleInfo['mirrorModule']
        self.mirrorModuleStatus = moduleInfo['mirror_options'][0]
        # Translation function for mirroring.
        self.mirrorTranslationFunc = moduleInfo['mirror_options'][1]
        # Rotation function for mirroring.
        self.mirrorRotationFunc = moduleInfo['mirror_options'][2]
        # Variables to set visibility attributes for hierarchy, orientation representations.
        self.showHierarchy = moduleInfo['node_compnts'][0]
        self.showOrientation = moduleInfo['node_compnts'][1]
        # Module handle colour.
        self.modHandleColour = moduleInfo['handle_colour'] - 1
        # Module namespace.
        self.moduleNamespace = moduleInfo['module_Namespace']
        # Generated mirror module namespace
        self.mirror_moduleNamespace = moduleInfo['mirror_module_Namespace']
        # Module container name.
        self.moduleContainer = self.moduleNamespace + ':module_container'

    def returnNodeInfoTransformation(self, numNodes):
        """
        This method calculates the position(s) for module node(s) based on their quantity and provided length
        from the UI. It also takes into account the offset position of the module from the origin, based on the
        creation plane for the module.
        """
        # List to record the positions.
        self.initNodePos = []
        if self.mirrorModule:
            self.moduleOffset = self.moduleOffset * -1
        # Axis for offset.
        axisForOffset = {'XY':'Z', 'YZ':'X', 'XZ':'Y'}[self.onPlane]
        # Record the position of the root node for the module.
        if axisForOffset == 'X':
            self.initNodePos.append([self.moduleOffset, 0, 0])
        if axisForOffset == 'Y':
            self.initNodePos.append([0, self.moduleOffset, 0])
        if axisForOffset == 'Z':
            self.initNodePos.append([0, 0, self.moduleOffset])
        # If the module has single node, return.
        if self.moduleLen == 0 or self.numNodes == 1:
            return
        # Increment for subsequent nodes in the module after root.
        increment = self.moduleLen / (numNodes - 1)
        # Calculate and append the node positions.
        incrementAxis = {'XY':'Y', 'YZ':'Y', 'XZ':'X'}[self.onPlane]
        if incrementAxis == 'Y':
            posIncrement = [0, 1, 0]
        if incrementAxis == 'X':
            posIncrement = [1, 0, 0]
        for i in range(numNodes - 1):
            self.initNodePos.append(map(lambda x,y:x+y, [c*increment for c in posIncrement], self.initNodePos[-1]))

    def createJointNodeModule(self):
        """Create a joint node module."""
        mfunc.updateAllTransforms()
        #mfunc.forceSceneUpdate()
        # Set the current namespace to root.
        cmds.namespace(setNamespace=':')
        # Create a new namespace for the module.
        cmds.namespace(add=self.moduleNamespace)
        # Create the module container.
        moduleContainer = cmds.container(name=self.moduleContainer)
        # Create an empty group for containing module handle segments.
        self.moduleHandleSegmentGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleHandleSegmentCurveGrp')
        self.moduleParentRepresentationGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleParentRepresentationGrp')
        # Create an empty group for containing module hierarchy/orientation representations.
        self.moduleOrientationHierarchyRepresentationGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleOrientationHierarchyRepresentationGrp')
        # Create module representation group containing the above two groups.
        self.moduleRepresentationGrp = cmds.group([self.moduleHandleSegmentGrp, self.moduleOrientationHierarchyRepresentationGrp, self.moduleParentRepresentationGrp], name=self.moduleNamespace+':moduleRepresentationObjGrp')
        # Create module extras group.
        self.moduleExtrasGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleExtrasGrp')
        # Create group under module extras to keep clusters for scaling node handle shapes.
        self.moduleNodeHandleShapeScaleClusterGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleNodeHandleShapeScaleClusterGrp', parent=self.moduleExtrasGrp)
        # Create main module group.
        self.moduleGrp = cmds.group([self.moduleRepresentationGrp, self.moduleExtrasGrp], name=self.moduleNamespace+':moduleGrp')
        # Add a custom attribute to the module group to store the number of nodes.
        cmds.addAttr(self.moduleGrp, attributeType='short', longName='numberOfNodes', defaultValue=self.numNodes, keyable=False)
        cmds.addAttr(self.moduleGrp, dataType='string', longName='nodeOrient', keyable=False)
        cmds.setAttr(self.moduleGrp+'.nodeOrient', self.nodeAxes, type='string')
        cmds.addAttr(self.moduleGrp, dataType='string', longName='moduleParent', keyable=False)
        cmds.setAttr(self.moduleGrp+'.moduleParent', 'None', type='string')
        cmds.addAttr(self.moduleGrp, dataType='string', longName='onPlane', keyable=False)
        cmds.setAttr(self.moduleGrp+'.onPlane', '+'+self.onPlane, type='string')
        cmds.addAttr(self.moduleGrp, dataType='string', longName='mirrorTranslation', keyable=False)
        cmds.setAttr(self.moduleGrp+'.mirrorTranslation', self.mirrorTranslationFunc, type='string')
        if self.mirrorModule:
            cmds.setAttr(self.moduleGrp+'.onPlane', '-'+self.onPlane, type='string')
        if self.mirrorModuleStatus == 'On':
            cmds.addAttr(self.moduleGrp, dataType='string', longName='mirrorModuleNamespace', keyable=False)
            cmds.setAttr(self.moduleGrp+'.mirrorModuleNamespace', self.mirror_moduleNamespace, type='string')
            cmds.addAttr(self.moduleGrp, dataType='string', longName='mirrorRotation', keyable=False)
            cmds.setAttr(self.moduleGrp+'.mirrorRotation', self.mirrorRotationFunc, type='string')
        # Create a group for proxy geometry.
        if self.proxyGeoStatus:
            if self.proxyGeoElbow or self.proxyGeoBones:
                self.proxyGeoGrp = cmds.group(empty=True, name=self.moduleNamespace+':proxyGeometryGrp')
                cmds.setAttr(self.proxyGeoGrp+'.overrideEnabled', 1)
                cmds.setAttr(self.proxyGeoGrp+'.overrideDisplayType', 2)
                if self.proxyGeoElbow:
                    cmds.addAttr(self.proxyGeoGrp, dataType='string', longName='elbowType', keyable=False)
                    cmds.setAttr(self.proxyGeoGrp+'.elbowType', self.proxyElbowType, type='string', lock=True)
                if self.mirrorModuleStatus == 'On':
                    cmds.addAttr(self.proxyGeoGrp, dataType='string', longName='mirrorInstance', keyable=False)
                    cmds.setAttr(self.proxyGeoGrp+'.mirrorInstance', self.proxyGeoMirrorInstance, type='string', lock=True)
        # Create module joints group, under the module group.
        self.moduleJointsGrp = cmds.group(empty=True, parent=self.moduleGrp, name=self.moduleNamespace+':moduleJointsGrp')
        # Initialize a list to contain created module node joints.
        self.joints = []
        # Get the positions of the module nodes, where the called method updates the self.initNodePos.
        self.returnNodeInfoTransformation(self.numNodes)
        # Move the joints group to the start position for the first joint node.
        cmds.xform(self.moduleJointsGrp, worldSpace=True, translation=self.initNodePos[0])
        # Create the module nodes (joints) by their position and name them accordingly.
        index = 0
        for nodePos in self.initNodePos:
            if index == 0:
                jointName = cmds.joint(name=self.moduleNamespace+':root_node_transform', position=nodePos, radius=0.0, scaleCompensate=False)
            elif nodePos == self.initNodePos[-1]:
                jointName = cmds.joint(name=self.moduleNamespace+':end_node_transform', position=nodePos, radius=0.0, scaleCompensate=False)
            else:
                jointName = cmds.joint(name=self.moduleNamespace+':node_%s_transform'%(index), position=nodePos, radius=0.0, scaleCompensate=False)
            cmds.setAttr(jointName+'.drawStyle', 2)
            cmds.setAttr(jointName+'.rotateX', keyable=False)
            cmds.setAttr(jointName+'.rotateY', keyable=False)
            cmds.setAttr(jointName+'.rotateZ', keyable=False)
            cmds.setAttr(jointName+'.scaleX', keyable=False)
            cmds.setAttr(jointName+'.scaleY', keyable=False)
            cmds.setAttr(jointName+'.scaleZ', keyable=False)
            cmds.setAttr(jointName+'.visibility', keyable=False, channelBox=False)
            cmds.setAttr(jointName+'.radius', keyable=False, channelBox=False)
            self.joints.append(jointName)
            index += 1
        # Orient the joints.
        cmds.select(self.joints[0], replace=True)
        # For orientation we'll use the axis perpendicular to the creation plane as the up axis for secondary axis orient.
        secondAxisOrientation = {'XY':'z', 'YZ':'x', 'XZ':'y'}[self.onPlane] + 'up'
        cmds.joint(edit=True, orientJoint=self.nodeAxes.lower(), secondaryAxisOrient=secondAxisOrientation, zeroScaleOrient=True, children=True)

        if self.mirrorModule and self.mirrorRotationFunc == 'Behaviour':
            mirrorPlane = {'XY':False, 'YZ':False, 'XZ':False}
            mirrorPlane[self.onPlane] = True
            mirroredJoints = cmds.mirrorJoint(self.joints[0], mirrorXY=mirrorPlane['XY'], mirrorYZ=mirrorPlane['YZ'], mirrorXZ=mirrorPlane['XZ'], mirrorBehavior=True)
            cmds.delete(self.joints[0])
            self.joints = []
            for joint in mirroredJoints:
                newJoint = cmds.rename(joint, self.moduleNamespace+':'+joint)
                self.joints.append(newJoint)
        # Orient the end joint node, if the module contains more than one joint node.
        if self.numNodes > 1:
            cmds.setAttr(self.joints[-1]+'.jointOrientX', 0)
            cmds.setAttr(self.joints[-1]+'.jointOrientY', 0)
            cmds.setAttr(self.joints[-1]+'.jointOrientZ', 0)
        # Clear selection after joint orientation.
        cmds.select(clear=True)
        # Add the module transform to the module, at the position of the root node.
        moduleTransform = objects.load_xhandleShape(self.moduleNamespace+'_handle', 24, True)
        cmds.setAttr(moduleTransform[0]+'.localScaleX', 0.26)
        cmds.setAttr(moduleTransform[0]+'.localScaleY', 0.26)
        cmds.setAttr(moduleTransform[0]+'.localScaleZ', 0.26)
        cmds.setAttr(moduleTransform[0]+'.drawStyle', 8)
        cmds.setAttr(moduleTransform[0]+'.drawOrtho', 0)
        cmds.setAttr(moduleTransform[0]+'.wireframeThickness', 2)
        cmds.setAttr(moduleTransform[1]+'.scaleX', keyable=False)
        cmds.setAttr(moduleTransform[1]+'.scaleY', keyable=False)
        cmds.setAttr(moduleTransform[1]+'.scaleZ', keyable=False)
        cmds.setAttr(moduleTransform[1]+'.visibility', keyable=False)
        cmds.addAttr(moduleTransform[1], attributeType='float', longName='globalScale', hasMinValue=True, minValue=0, defaultValue=1, keyable=True)
        self.moduleTransform = cmds.rename(moduleTransform[1], self.moduleNamespace+':module_transform')
        tempConstraint = cmds.pointConstraint(self.joints[0], self.moduleTransform, maintainOffset=False)
        cmds.delete(tempConstraint)
        # Add the module transform to the module group.
        cmds.parent(self.moduleTransform, self.moduleGrp, absolute=True)
        # Set up constraints for the module transform.
        module_node_parentConstraint = cmds.parentConstraint(self.moduleTransform, self.moduleJointsGrp, maintainOffset=True, name=self.moduleNamespace+':moduleTransform_rootNode_parentConstraint')
        module_node_scaleConstraint = cmds.scaleConstraint(self.moduleTransform, self.moduleJointsGrp, maintainOffset=False, name=self.moduleNamespace+':moduleTransform_rootNode_scaleConstraint')
        cmds.connectAttr(self.moduleTransform+'.globalScale', self.moduleTransform+'.scaleX')
        cmds.connectAttr(self.moduleTransform+'.globalScale', self.moduleTransform+'.scaleY')
        cmds.connectAttr(self.moduleTransform+'.globalScale', self.moduleTransform+'.scaleZ')
        # Connect the scale attributes to an aliased 'globalScale' attribute (This could've been done on the raw def itself, but it was issuing a cycle; not sure why. But the DG eval was not cyclic).
        # Create hierarchy/orientation representation on joint node(s), depending on number of nodes in the module.
        containedNodes = self.createHandleControlRepresentation()
        if len(self.joints) == 1:
            self.moduleSingleOrientationRepresentationGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleSingleOrientationRepresentationGrp', parent=self.moduleRepresentationGrp)
            singleOrientationTransform = objects.createRawSingleOrientationRepresentation()
            cmds.setAttr(singleOrientationTransform+'.scale', 0.65, 0.65, 0.65, type='double3')
            cmds.makeIdentity(singleOrientationTransform, scale=True, apply=True)
            #if self.mirrorModule and self.mirrorRotationFunc == 'Behaviour':
                #for axis in self.onPlane:
                    #cmds.setAttr(singleOrientationTransform+'.scale'+axis, -1)
                    #cmds.makeIdentity(singleOrientationTransform, scale=True, apply=True)
            cmds.parent(singleOrientationTransform, self.moduleSingleOrientationRepresentationGrp, absolute=True)
            cmds.rename(singleOrientationTransform, self.moduleNamespace+':'+singleOrientationTransform)
            cmds.xform(self.moduleSingleOrientationRepresentationGrp, worldSpace=True, absolute=True, translation=cmds.xform(self.joints[0], query=True, worldSpace=True, translation=True))
            cmds.parentConstraint(self.joints[0], self.moduleSingleOrientationRepresentationGrp, maintainOffset=False, name=self.moduleSingleOrientationRepresentationGrp+'_parentConstraint')
            cmds.scaleConstraint(self.moduleTransform, self.moduleSingleOrientationRepresentationGrp, maintainOffset=False, name=self.moduleSingleOrientationRepresentationGrp+'_scaleConstraint')
        for joint in self.joints:
            xhandle = objects.load_xhandleShape(joint, self.modHandleColour)
            cmds.setAttr(xhandle[0]+'.localScaleX', 0.089)
            cmds.setAttr(xhandle[0]+'.localScaleY', 0.089)
            cmds.setAttr(xhandle[0]+'.localScaleZ', 0.089)
            #cmds.parent(xhandle[0], joint, relative=True, shape=True)
            #cmds.delete(xhandle[1])
            cmds.setAttr(xhandle[0]+'.ds', 5)
        # If there's more than one node, create orientation/hierarchy representations for all joints, except for the end joint.
        # Also unparent the individual joints in the oriented joint chain to the joint group. This is needed only if there are more than one
        # joint in the module; then the unparenting will begin from the second joint, since the first (start) is already under joints group.
        if len(self.joints) > 1:
            for joint in self.joints[1:]:
                cmds.parent(joint, self.moduleJointsGrp, absolute=True)
            containedNodes += self.createOrientationHierarchyRepresentationOnNodes()
        # Clear selection.
        cmds.select(clear=True)
        # If the module contains only one node then delete the handle segment and orientation/hierarchy representation groups, since they're not needed.
        if self.numNodes == 1:
            cmds.delete([self.moduleHandleSegmentGrp, self.moduleOrientationHierarchyRepresentationGrp])

        containedNodes += self.createHierarchySegmentForModuleParentingRepresentation()

        if self.proxyGeoStatus:
            if self.proxyGeoElbow:
                self.createProxyGeo_elbows(self.proxyElbowType)
            if self.proxyGeoBones:
                self.createProxyGeo_bones()

        # Add the module group to the contained nodes list.
        containedNodes += [self.moduleGrp]
        # Add the contained nodes to the module container.
        mfunc.addNodesToContainer(self.moduleContainer, containedNodes, includeHierarchyBelow=True, includeShapes=True)
        # Publish contents to the container.
        # Publish the orientation representation control for module joints.
        for joint in self.joints:
            jointName = mfunc.stripMRTNamespace(joint)[1]   # Nice name for the joint, used as published name.
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[joint+'.translate', jointName+'_translate'])
            if joint != self.joints[-1]:
                jointOrientationRepresentation = joint + '_orientation_representation_transform'
                jointOrientationRotateAxis = self.nodeAxes[0]
                jointOrientationRepresentationName = mfunc.stripMRTNamespace(jointOrientationRepresentation)[1]
                cmds.container(self.moduleContainer, edit=True, publishAndBind=[jointOrientationRepresentation+'.rotate'+jointOrientationRotateAxis, jointOrientationRepresentationName+'_rotate'+jointOrientationRotateAxis])

        # Publish the attributes for the module transform.
        moduleTransformName = mfunc.stripMRTNamespace(self.moduleTransform)[1]
        cmds.container(self.moduleContainer, edit=True, publishAndBind=[self.moduleTransform+'.translate', moduleTransformName+'_translate'])
        cmds.container(self.moduleContainer, edit=True, publishAndBind=[self.moduleTransform+'.rotate', moduleTransformName+'_rotate'])
        cmds.container(self.moduleContainer, edit=True, publishAndBind=[self.moduleTransform+'.globalScale', moduleTransformName+'_globalScale'])
        # If the module contains only single node, publish its orientation control.
        if len(self.joints) == 1:
            singleOrientationTransform = self.moduleNamespace+':single_orientation_representation_transform'
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[singleOrientationTransform+'.rotate', 'single_orientation_representation_transform_rotate'])
        # Add and publish custom attributes on the module transform.
        self.addCustomAttributesOnModuleTransform()
        if self.numNodes > 1:
            self.connectCustomOrientationReprToBoneProxies()
        #cmds.setAttr(self.moduleTransform+'.globalScale', 4)

    def createHierarchySegmentForModuleParentingRepresentation(self, *args):
        containedNodes  = []
        #handleSegmentParts = objects.createRawHandleSegment(3)
        handleSegmentParts = objects.createRawSegmentCurve(3)
        hierarchyRepresentation = objects.createRawHierarchyRepresentation('X')
        cmds.setAttr(hierarchyRepresentation+'.scale', 1.0, 1.0, 1.0, type='double3')
        cmds.makeIdentity(hierarchyRepresentation, scale=True, apply=True)
        hierarchyRepresentationShape = cmds.listRelatives(hierarchyRepresentation, children=True, shapes=True)[0]
        cmds.setAttr(hierarchyRepresentationShape+'.overrideColor', 2)
        for node in handleSegmentParts[4]:
            if cmds.objExists(node):
                containedNodes.append(cmds.rename(node, self.moduleNamespace+':moduleParentRepresentationSegment_clusterParts_'+node))
        cmds.pointConstraint(self.joints[0], handleSegmentParts[5], maintainOffset=False, name=self.moduleNamespace+':moduleParentRepresentationSegment_startLocator_pointConstraint')
        cmds.parent([handleSegmentParts[1], handleSegmentParts[2][1], handleSegmentParts[3][1], handleSegmentParts[5], handleSegmentParts[6]], self.moduleParentRepresentationGrp, absolute=True)
        cmds.pointConstraint(handleSegmentParts[5], handleSegmentParts[6], hierarchyRepresentation, maintainOffset=False, name=self.moduleNamespace+':moduleParentRepresentationSegment_hierarchyRepresentation_pointConstraint')
        # Scale constrain the hierarchy representation to the joint in iteration.
        cmds.scaleConstraint(self.joints[0], hierarchyRepresentation, maintainOffset=False, name=self.moduleNamespace+':moduleParentRepresentationSegment_hierarchyRepresentation_scaleConstraint')
        cmds.aimConstraint(handleSegmentParts[5], hierarchyRepresentation, maintainOffset=False, aimVector=[1.0, 0.0, 0.0], upVector=[0.0, 1.0, 0.0], worldUpVector=[0.0, 1.0, 0.0], worldUpType='objectRotation', worldUpObject=handleSegmentParts[5], name=self.moduleNamespace+':moduleParentRepresentationSegment_hierarchyRepresentation_aimConstraint')
        # Parent the orientation representation pre-transform and the hierarchy representation to their appropriate group.
        cmds.parent(hierarchyRepresentation, self.moduleParentRepresentationGrp, absolute=True)
        cmds.rename(hierarchyRepresentation, self.moduleNamespace+':moduleParentRepresentationSegment_'+hierarchyRepresentation)
        tempConstraint = cmds.pointConstraint(self.joints[0], handleSegmentParts[6], maintainOffset=False)
        cmds.delete(tempConstraint)
        cmds.rename(handleSegmentParts[1], self.moduleNamespace+':moduleParentRepresentationSegment_'+handleSegmentParts[1])
        # Rename the 'start' and 'end' locators which constrain the cluster handles.
        cmds.rename(handleSegmentParts[5], self.moduleNamespace+':moduleParentRepresentationSegment_'+handleSegmentParts[5])
        cmds.rename(handleSegmentParts[6], self.moduleNamespace+':moduleParentRepresentationSegment_'+handleSegmentParts[6])
        # Rename the cluster handles.
        newStartClusterHandle = cmds.rename(handleSegmentParts[2][1], self.moduleNamespace+':moduleParentRepresentationSegment_'+handleSegmentParts[2][1])
        newEndClusterHandle = cmds.rename(handleSegmentParts[3][1], self.moduleNamespace+':moduleParentRepresentationSegment_'+handleSegmentParts[3][1])
        # Rename the constraints on the cluster handles. Here, it is necessary to specify the constraints by their DAG path.
        cmds.rename(newStartClusterHandle+'|'+handleSegmentParts[7].rpartition('|')[2], self.moduleNamespace+':moduleParentRepresentationSegment_'+handleSegmentParts[7].rpartition('|')[2])
        cmds.rename(newEndClusterHandle + '|'+handleSegmentParts[8].rpartition('|')[2], self.moduleNamespace+':moduleParentRepresentationSegment_'+handleSegmentParts[8].rpartition('|')[2])
        ##startClusterGrpParts = cmds.rename('handleControlSegmentCurve_StartClusterGroupParts', newStartClusterHandle+'_ClusterGroupParts')
        ##endClusterGrpParts = cmds.rename('handleControlSegmentCurve_EndClusterGroupParts', newEndClusterHandle+'_ClusterGroupParts')
        startClusterGrpParts = cmds.rename('segmentCurve_startClusterGroupParts', newStartClusterHandle+'_clusterGroupParts')
        endClusterGrpParts = cmds.rename('segmentCurve_endClusterGroupParts', newEndClusterHandle+'_clusterGroupParts')
        # Clear the selection, and force an update on DG.
        cmds.select(clear=True)
        cmds.setAttr(self.moduleParentRepresentationGrp+'.visibility', 0)
        # Collect the nodes.
        containedNodes.extend([newStartClusterHandle+'Cluster', newEndClusterHandle+'Cluster', startClusterGrpParts, endClusterGrpParts])
        return containedNodes

    def createHandleControlRepresentation(self):
        """
        Creates handle control representation objects on module nodes when called. It also creates segments between node(s) to
        represent how the module nodes are connected.
        """
        mfunc.updateAllTransforms()
        #mfunc.forceSceneUpdate()
        # List to collect non DAG nodes as they're generated, so that they can be added to the module container.
        containedNodes = []
        # Create handle(s) on every module node(s)(joint) in iteration.
        i = 0
        for joint in self.joints:
            # Create a raw handle object.
            ##handleNodes = objects.createRawHandle(self.modHandleColour)
            handleNodes = objects.createRawControlSurface(joint, self.modHandleColour)
            # Parent and then rename their shapes with the joint node.
            ##cmds.parent(handleNodes[1], joint, relative=True, shape=True)
            ##newHandleShape = cmds.rename(handleNodes[1], joint+'_'+handleNodes[1])
            newHandleShape = handleNodes[1]
            # Delete the empty transform for the raw handle objects.
            ##cmds.delete(handleNodes[0])
            # Select and add a cluster to the joint node, which will affect its shape node. The selection command is important here since it'll
            # update the DG in context to the joint with its new shape node. Otherwise the cluster will report 'no deformable objects' when
            # directly processing the joint or its shape node when passed in as the first argument.
            ##handleShapeScaleCluster = cmds.cluster(newHandleShape, relative=True, name=newHandleShape+'_handleShapeScaleCluster')
            handleShapeScaleCluster = cmds.cluster(newHandleShape, relative=True, name=newHandleShape+'_scaleCluster')
            # Parent the cluster handle appropriately and turn off its visibility.
            cmds.parent(handleShapeScaleCluster[1], self.moduleNodeHandleShapeScaleClusterGrp, absolute=True)
            cmds.setAttr(handleShapeScaleCluster[1]+'.visibility', 0)
            #cmds.xform(handleShapeScaleCluster[1], scalePivot=self.initNodePos[i])
            #cmds.sets(newHandleShape, add=handleShapeScaleCluster[0]+'Set')
            # Collect the cluster nodes.
            clusterNodes = cmds.listConnections(newHandleShape, source=True, destination=True)
            # Remove the tweak node.
            for node in clusterNodes:
                if cmds.nodeType(node) == 'tweak':
                    cmds.delete(node)
                    break
            # Update the cluster node list and collect it.
            clusterNodes = cmds.listConnections(newHandleShape, source=True, destination=True)
            containedNodes.extend(clusterNodes)
            # Create a locator and point constrain it to the joint node in iteration for indicating its world position. This will be needed later for utility purposes.
            worldPosLocator = cmds.spaceLocator(name=joint+'_worldPosLocator')[0]
            cmds.pointConstraint(joint, worldPosLocator, maintainOffset=False, name=self.moduleNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_worldPosLocator_pointConstraint')
            # Turn off its visibility and parent it accordingly.
            cmds.setAttr(worldPosLocator + '.visibility', 0)
            cmds.setAttr(newHandleShape+'.visibility', 0)
            cmds.parent(worldPosLocator, self.moduleHandleSegmentGrp, absolute=True)
            i += 1
        # If the module contains more the one node (joint), create segment representations between the joints in hierarchy.
        if len(self.joints) > 1:
            j = 0
            # Iterate through every joint except the last joint.
            for joint in self.joints[:-1]:
                # Create a raw segment object.
                ##handleSegmentParts = objects.createRawHandleSegment(self.modHandleColour)
                handleSegmentParts = objects.createRawSegmentCurve(self.modHandleColour)
                # Rename its associated non DAG nodes and collect them.
                for node in handleSegmentParts[4]:
                    if cmds.objExists(node):
                        containedNodes.append(cmds.rename(node, self.moduleNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_clusterParts_'+node))
                # Now set up DG connections with appropriate nodes to help limit the segment curve between the handle surfaces. This is done so that the length
                # of this segment curve can be used to adjust the length of the orientation representation control object, so that it always fits between
                # two node handle surfaces, even if they change in sizes.
                startClosestPointOnSurface = cmds.createNode('closestPointOnSurface', name=joint+'_'+handleSegmentParts[5]+'_closestPointOnSurface')
                ##cmds.connectAttr(joint+'_handleControlShape.worldSpace[0]', startClosestPointOnSurface+'.inputSurface')
                cmds.connectAttr(joint+'_controlShape.worldSpace[0]', startClosestPointOnSurface+'.inputSurface')
                cmds.connectAttr(self.joints[j+1]+'_worldPosLocator.translate', startClosestPointOnSurface+'.inPosition')
                cmds.connectAttr(startClosestPointOnSurface+'.position', handleSegmentParts[5]+'.translate')
                endClosestPointOnSurface = cmds.createNode('closestPointOnSurface', name=self.joints[j+1]+'_'+handleSegmentParts[6]+'_closestPointOnSurface')
                ##cmds.connectAttr(self.joints[j+1]+'_handleControlShape.worldSpace[0]', endClosestPointOnSurface+'.inputSurface')
                cmds.connectAttr(self.joints[j+1]+'_controlShape.worldSpace[0]', endClosestPointOnSurface+'.inputSurface')
                cmds.connectAttr(joint+'_worldPosLocator.translate', endClosestPointOnSurface+'.inPosition')
                cmds.connectAttr(endClosestPointOnSurface+'.position', handleSegmentParts[6]+'.translate')
                # Parent the segment and its related nodes to their associated group.
                cmds.parent([handleSegmentParts[1], handleSegmentParts[2][1], handleSegmentParts[3][1], handleSegmentParts[5], handleSegmentParts[6]], self.moduleHandleSegmentGrp, absolute=True)
                # Rename the nodes.
                # Rename the curve transform.
                cmds.rename(handleSegmentParts[1], self.moduleNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_'+handleSegmentParts[1])
                # Rename the 'start' and 'end' locators which constrain the cluster handles.
                cmds.rename(handleSegmentParts[5], joint+'_'+handleSegmentParts[5])
                cmds.rename(handleSegmentParts[6], self.joints[j+1]+'_'+handleSegmentParts[6])
                # Rename the cluster handles.
                newStartClusterHandle = cmds.rename(handleSegmentParts[2][1], self.moduleNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_'+handleSegmentParts[2][1])
                newEndClusterHandle = cmds.rename(handleSegmentParts[3][1], self.moduleNamespace+':'+mfunc.stripMRTNamespace(self.joints[j+1])[1]+'_'+handleSegmentParts[3][1])
                # Rename the constraints on the cluster handles. Here, it is necessary to specify the constraints by their DAG path.
                cmds.rename(newStartClusterHandle+'|'+handleSegmentParts[7].rpartition('|')[2], joint+'_'+handleSegmentParts[7].rpartition('|')[2])
                cmds.rename(newEndClusterHandle + '|'+handleSegmentParts[8].rpartition('|')[2], self.joints[j+1]+'_'+handleSegmentParts[8].rpartition('|')[2])
                ##startClusterGrpParts = cmds.rename('handleControlSegmentCurve_StartClusterGroupParts', newStartClusterHandle+'_ClusterGroupParts')
                startClusterGrpParts = cmds.rename('segmentCurve_startClusterGroupParts', newStartClusterHandle+'_clusterGroupParts')
                ##endClusterGrpParts = cmds.rename('handleControlSegmentCurve_EndClusterGroupParts', newEndClusterHandle+'_ClusterGroupParts')
                endClusterGrpParts = cmds.rename('segmentCurve_endClusterGroupParts', newEndClusterHandle+'_clusterGroupParts')
                # Clear the selection, and force an update on DG.
                cmds.select(clear=True)
                # Collect the nodes.
                containedNodes.extend([newStartClusterHandle+'Cluster', newEndClusterHandle+'Cluster', startClosestPointOnSurface, endClosestPointOnSurface, startClusterGrpParts, endClusterGrpParts])
                j += 1
        return containedNodes

    def createOrientationHierarchyRepresentationOnNodes(self):
        """This method creates orientation and hierarchy representation object(s) for every node except the last."""
        # List to collect non DAG nodes as they're generated, so that they can be added to the module container.
        containedNodes = []
        # Create representation objects for every module node(s)(joint) except the last in iteration.
        index = 0
        for joint in self.joints[:-1]:
            # Create raw representation objects.
            hierarchyRepresentation = objects.createRawHierarchyRepresentation(self.nodeAxes[0])
            orientationRepresentationNodes = objects.createRawOrientationRepresentation(self.nodeAxes[0])
            if self.mirrorModule and self.mirrorRotationFunc == 'Behaviour':
                cmds.setAttr(orientationRepresentationNodes[0]+'.scale'+self.nodeAxes[2], -1)
                cmds.makeIdentity(orientationRepresentationNodes[0], scale=True, apply=True)
            # Point constrain the orientation representation pre-transform to the joint in iteration.
            cmds.pointConstraint(joint, orientationRepresentationNodes[1], maintainOffset=False, name=self.moduleNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_orientation_representation_transformGroup_pointConstraint')
            # Get the name(reference) for the 'start' and 'end' locators(while creating the node segment representations). These locators are on the node handle shape surfaces via CPS.
            ##startLocator = joint + '_handleControlSegmentCurve_startLocator'
            ##endLocator = self.joints[index+1] + '_handleControlSegmentCurve_endLocator'
            startLocator = joint + '_segmentCurve_startLocator'
            endLocator = self.joints[index+1] + '_segmentCurve_endLocator'
            # Point constrain the hierarchy representation to the start and end locators.
            cmds.pointConstraint(startLocator, endLocator, hierarchyRepresentation, maintainOffset=False, name=joint+'_hierarchy_representation_pointConstraint')
            # Scale constrain the hierarchy representation to the joint in iteration.
            cmds.scaleConstraint(joint, hierarchyRepresentation, maintainOffset=False, name=joint+'_hierarchy_representation_scaleConstraint')
            # Aim constrain the orientation representation pre-transform and the hierarchy representation with the next joint in iteration.
            aimVector = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[0]]
            upVector = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[1]]
            cmds.aimConstraint(self.joints[index+1], orientationRepresentationNodes[1], maintainOffset=False, aimVector=aimVector, upVector=upVector, worldUpVector=upVector, worldUpType='objectRotation', worldUpObject=joint, name=self.moduleNamespace+':'+mfunc.stripMRTNamespace(self.joints[index+1])[1]+'_orientation_representation_transformGroup_aimConstraint')
            cmds.aimConstraint(self.joints[index+1], hierarchyRepresentation, maintainOffset=False, aimVector=aimVector, upVector=upVector, worldUpVector=upVector, worldUpType='objectRotation', worldUpObject=joint, name=self.moduleNamespace+':'+mfunc.stripMRTNamespace(self.joints[index+1])[1]+'_hierarchy_representation_aimConstraint')
            # Parent the orientation representation pre-transform and the hierarchy representation to their appropriate group.
            cmds.parent(hierarchyRepresentation, self.moduleOrientationHierarchyRepresentationGrp, absolute=True)
            cmds.parent(orientationRepresentationNodes[1], self.moduleOrientationHierarchyRepresentationGrp, absolute=True)
            # Point constrain the orientation representation to the start locator, on the surface of the shape node of the joint in iteration.
            ##cmds.pointConstraint(joint+'_handleControlSegmentCurve_startLocator', orientationRepresentationNodes[0], maintainOffset=True, name=self.moduleNamespace+':'+orientationRepresentationNodes[0]+'_basePointConstraint')
            cmds.pointConstraint(joint+'_segmentCurve_startLocator', orientationRepresentationNodes[0], maintainOffset=True, name=self.moduleNamespace+':'+orientationRepresentationNodes[0]+'_basePointConstraint')
            # Depending on the node aim axis, connect the scale attributes for the orientation representation. The scaling along the aim axis will
            # be the size of the orientation representation, proportional to the arc length of the segment curve between two nodes.
            if self.nodeAxes[0] == 'X':
                ##arclen = cmds.arclen(joint+'_handleControlSegmentCurve', constructionHistory=True)
                arclen = cmds.arclen(joint+'_segmentCurve', constructionHistory=True)
                cmds.connectAttr(arclen+'.arcLength', orientationRepresentationNodes[0]+'.scaleX')
                cmds.connectAttr(self.moduleTransform+'.globalScale', orientationRepresentationNodes[0]+'.scaleY')
                cmds.connectAttr(self.moduleTransform+'.globalScale', orientationRepresentationNodes[0]+'.scaleZ')
                ##cmds.rename(arclen, joint+'_handleControlSegmentCurve_curveInfo')
                ##containedNodes.append(joint+'_handleControlSegmentCurve_curveInfo')
                cmds.rename(arclen, joint+'_segmentCurve_curveInfo')
                containedNodes.append(joint+'_segmentCurve_curveInfo')
            if self.nodeAxes[0] == 'Y':
                ##arclen = cmds.arclen(joint+'_handleControlSegmentCurve', constructionHistory=True)
                arclen = cmds.arclen(joint+'_segmentCurve', constructionHistory=True)
                cmds.connectAttr(arclen+'.arcLength', orientationRepresentationNodes[0]+'.scaleY')
                cmds.connectAttr(self.moduleTransform+'.globalScale', orientationRepresentationNodes[0]+'.scaleX')
                cmds.connectAttr(self.moduleTransform+'.globalScale', orientationRepresentationNodes[0]+'.scaleZ')
                ##cmds.rename(arclen, joint+'_handleControlSegmentCurve_curveInfo')
                ##containedNodes.append(joint+'_handleControlSegmentCurve_curveInfo')
                cmds.rename(arclen, joint+'_segmentCurve_curveInfo')
                containedNodes.append(joint+'_segmentCurve_curveInfo')
            if self.nodeAxes[0] == 'Z':
                ##arclen = cmds.arclen(joint+'_handleControlSegmentCurve', constructionHistory=True)
                arclen = cmds.arclen(joint+'_segmentCurve', constructionHistory=True)
                cmds.connectAttr(arclen+'.arcLength', orientationRepresentationNodes[0]+'.scaleZ')
                cmds.connectAttr(self.moduleTransform+'.globalScale', orientationRepresentationNodes[0]+'.scaleX')
                cmds.connectAttr(self.moduleTransform+'.globalScale', orientationRepresentationNodes[0]+'.scaleY')
                ##cmds.rename(arclen, joint+'_handleControlSegmentCurve_curveInfo')
                ##containedNodes.append(joint+'_handleControlSegmentCurve_curveInfo')
                cmds.rename(arclen, joint+'_segmentCurve_curveInfo')
                containedNodes.append(joint+'_segmentCurve_curveInfo')

            # Rename the hierarchy representation, orientation representation and its pre-transform.
            cmds.rename(hierarchyRepresentation, joint+'_'+hierarchyRepresentation)
            cmds.rename(orientationRepresentationNodes[0], self.moduleNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_'+orientationRepresentationNodes[0])
            cmds.rename(orientationRepresentationNodes[1], self.moduleNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_'+orientationRepresentationNodes[1])
            index += 1
        return containedNodes

    def createSplineNodeModule(self, *args):
        """Create a spline node module."""
        #mfunc.forceSceneUpdate()
        mfunc.updateAllTransforms()
        # Set the current namespace to root.
        cmds.namespace(setNamespace=':')
        # Create a new namespace for the module.
        cmds.namespace(add=self.moduleNamespace)
        # Create the module container.
        moduleContainer = cmds.container(name=self.moduleContainer)
        # Create an empty group for containing module handle segments.
        self.moduleSplineCurveGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleSplineCurveGrp')
        # Create an empty group for containing module hierarchy/orientation representations.
        self.moduleHandleGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleHandleGrp')
        self.moduleParentRepresentationGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleParentRepresentationGrp')
        # Create an empty group for containing splineAdjustCurveTransform.
        self.moduleSplineAdjustCurveGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleSplineAdjustCurveGrp')
        # Create an empty group for containing orientation representation transforms and nodes.
        self.moduleOrientationRepresentationGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleOrientationRepresentationGrp')
        # Create a module representation group containing the above four groups.
        self.moduleRepresentationGrp = cmds.group([self.moduleSplineAdjustCurveGrp, self.moduleSplineCurveGrp, self.moduleHandleGrp, self.moduleOrientationRepresentationGrp, self.moduleParentRepresentationGrp], name=self.moduleNamespace+':moduleRepresentationObjGrp')
        # Create a main module group, with the representation group as the child.
        self.moduleGrp = cmds.group([self.moduleRepresentationGrp], name=self.moduleNamespace+':moduleGrp')
        # Add a custom attribute to the module group to store the number of nodes.
        cmds.addAttr(self.moduleGrp, attributeType='short', longName='numberOfNodes', defaultValue=self.numNodes, keyable=False)
        cmds.addAttr(self.moduleGrp, dataType='string', longName='nodeOrient', keyable=False)
        cmds.setAttr(self.moduleGrp+'.nodeOrient', self.nodeAxes, type='string')
        cmds.addAttr(self.moduleGrp, dataType='string', longName='moduleParent', keyable=False)
        cmds.setAttr(self.moduleGrp+'.moduleParent', 'None', type='string')
        cmds.addAttr(self.moduleGrp, dataType='string', longName='onPlane', keyable=False)
        cmds.setAttr(self.moduleGrp+'.onPlane', '+'+self.onPlane, type='string')
        cmds.addAttr(self.moduleGrp, dataType='string', longName='mirrorTranslation', keyable=False)
        cmds.setAttr(self.moduleGrp+'.mirrorTranslation', self.mirrorTranslationFunc, type='string')
        if self.mirrorModule:
            cmds.setAttr(self.moduleGrp+'.onPlane', '-'+self.onPlane, type='string')
        if self.mirrorModuleStatus == 'On':
            cmds.addAttr(self.moduleGrp, dataType='string', longName='mirrorModuleNamespace', keyable=False)
            cmds.setAttr(self.moduleGrp+'.mirrorModuleNamespace', self.mirror_moduleNamespace, type='string')
            cmds.addAttr(self.moduleGrp, dataType='string', longName='mirrorRotation', keyable=False)
            cmds.setAttr(self.moduleGrp+'.mirrorRotation', self.mirrorRotationFunc, type='string')
        # Create a group for proxy geometry.
        if self.proxyGeoStatus and self.proxyGeoElbow:
            self.proxyGeoGrp = cmds.group(empty=True, name=self.moduleNamespace+':proxyGeometryGrp')
            cmds.setAttr(self.proxyGeoGrp+'.overrideEnabled', 1)
            cmds.setAttr(self.proxyGeoGrp+'.overrideDisplayType', 2)
            cmds.addAttr(self.proxyGeoGrp, dataType='string', longName='elbowType', keyable=False)
            cmds.setAttr(self.proxyGeoGrp+'.elbowType', self.proxyElbowType, type='string', lock=True)
            if self.mirrorModuleStatus == 'On':
                cmds.addAttr(self.proxyGeoGrp, dataType='string', longName='mirrorInstance', keyable=False)
                cmds.setAttr(self.proxyGeoGrp+'.mirrorInstance', self.proxyGeoMirrorInstance, type='string', lock=True)
        # Create a module joints group, under the module group.
        self.moduleJointsGrp = cmds.group(empty=True, parent=self.moduleGrp, name=self.moduleNamespace+':moduleJointsGrp')
        # Initialize a list to contain created module node joints.
        self.joints = []
        # Get the positions of the module nodes, where the called method updates the self.initNodePos.
        self.returnNodeInfoTransformation(numNodes=4)
        # Initialize a list to collect non DAG nodes, for adding to the module container.
        collectedNodes = []

        splineNodeCurve = cmds.curve(degree=3, point=self.initNodePos, worldSpace=True)
        cmds.xform(splineNodeCurve, centerPivots=True)
        cmds.rebuildCurve(splineNodeCurve, constructionHistory=False, replaceOriginal=True, rebuildType=0, degree=3, endKnots=True, keepEndPoints=True, keepRange=0, keepControlPoints=False, keepTangents=False, spans=cmds.getAttr(splineNodeCurve+'.spans'), tolerance=0.01)
        newSplineNodeCurve = cmds.rename(splineNodeCurve, self.moduleNamespace+':splineNode_curve')
        cmds.displaySmoothness(newSplineNodeCurve, pointsWire=32)
        cmds.toggle(newSplineNodeCurve, template=True, state=True)
        cmds.parent(newSplineNodeCurve, self.moduleSplineCurveGrp, absolute=True)

        cmds.select(clear=True)
        self.returnNodeInfoTransformation(self.numNodes)
        self.joints = []
        for index in range(len(self.initNodePos)):
            if index == 0:
                jointName = cmds.joint(name=self.moduleNamespace+':root_node_transform', position=self.initNodePos[index], radius=0.0)
            elif index == len(self.initNodePos)-1:
                jointName = cmds.joint(name=self.moduleNamespace+':end_node_transform', position=self.initNodePos[index], radius=0.0)
            else:
                jointName = cmds.joint(name=self.moduleNamespace+':node_%s_transform'%(index), position=self.initNodePos[index], radius=0.0)
            self.joints.append(jointName)
        # Orient the joints.
        cmds.select(self.joints[0], replace=True)
        # For orientation we'll use the axis perpendicular to the creation plane as the up axis for secondary axis orient.
        secondAxisOrientation = {'XY':'z', 'YZ':'x', 'XZ':'y'}[self.onPlane] + 'up'
        cmds.joint(edit=True, orientJoint=self.nodeAxes.lower(), secondaryAxisOrient=secondAxisOrientation, zeroScaleOrient=True, children=True)
        cmds.parent(self.joints[0], self.moduleJointsGrp, absolute=True)
        if self.mirrorModule and self.mirrorRotationFunc == 'Behaviour':
            mirrorPlane = {'XY':False, 'YZ':False, 'XZ':False}
            mirrorPlane[self.onPlane] = True
            mirroredJoints = cmds.mirrorJoint(self.joints[0], mirrorXY=mirrorPlane['XY'], mirrorYZ=mirrorPlane['YZ'], mirrorXZ=mirrorPlane['XZ'], mirrorBehavior=True)
            cmds.delete(self.joints[0])
            self.joints = []
            for joint in mirroredJoints:
                newJoint = cmds.rename(joint, self.moduleNamespace+':'+joint)
                self.joints.append(newJoint)
        # Orient the end joint node.
        cmds.setAttr(self.joints[-1]+'.jointOrientX', 0)
        cmds.setAttr(self.joints[-1]+'.jointOrientY', 0)
        cmds.setAttr(self.joints[-1]+'.jointOrientZ', 0)
        # Clear selection after joint orientation.
        cmds.select(clear=True)
        # Unparent the spline node joints.
        for joint in self.joints[1:]:
            cmds.parent(joint, self.moduleJointsGrp, absolute=True)

        u_parametersOnCurve = [1.0/(len(self.joints)-1)*c for c in xrange(len(self.joints))]
        for index in range(len(self.joints)):
            pointOnCurveInfo = cmds.createNode('pointOnCurveInfo', name=self.moduleNamespace+':'+mfunc.stripMRTNamespace(self.joints[index])[1]+'_pointOnCurveInfo')
            cmds.connectAttr(self.moduleNamespace+':splineNode_curveShape.worldSpace', pointOnCurveInfo+'.inputCurve')
            cmds.connectAttr(pointOnCurveInfo+'.position', self.joints[index]+'.translate')
            cmds.setAttr(pointOnCurveInfo+'.parameter', u_parametersOnCurve[index])
            collectedNodes.append(pointOnCurveInfo)

        clusterWeights = sorted([1.0/3*c for c in xrange(4)], reverse=True)[:-1]
        startCluster = cmds.cluster([newSplineNodeCurve+'.cv[%s]'%(cv) for cv in xrange(0, 3)], relative=True, name=newSplineNodeCurve+'_startCluster')
        cmds.setAttr(startCluster[1]+'.visibility', 0)
        cmds.parent(startCluster[1], self.moduleSplineCurveGrp, absolute=True)
        for (cv, weight) in zip(xrange(0, 3), clusterWeights):
            cmds.percent(startCluster[0], '%s.cv[%s]'%(newSplineNodeCurve, cv), value=weight)
        endCluster = cmds.cluster([newSplineNodeCurve+'.cv[%s]'%(cv) for cv in xrange(3, 0, -1)], relative=True, name=newSplineNodeCurve+'_endCluster')
        cmds.setAttr(endCluster[1]+'.visibility', 0)
        cmds.parent(endCluster[1], self.moduleSplineCurveGrp, absolute=True)
        for (cv, weight) in zip(xrange(3, 0, -1), clusterWeights):
            cmds.percent(endCluster[0], '%s.cv[%s]'%(newSplineNodeCurve, cv), value=weight)
        collectedNodes.extend([startCluster[0], endCluster[0]])

        # Add the module transform to the module, at the position of the root node.

        startHandle = objects.load_xhandleShape(self.moduleNamespace+'_startHandle', 11, True)
        cmds.setAttr(startHandle[0]+'.localScaleX', 0.4)
        cmds.setAttr(startHandle[0]+'.localScaleY', 0.4)
        cmds.setAttr(startHandle[0]+'.localScaleZ', 0.4)
        cmds.setAttr(startHandle[0]+'.drawStyle', 3)
        cmds.setAttr(startHandle[0]+'.wireframeThickness', 2)
        cmds.setAttr(startHandle[1]+'.rotateX', keyable=False)
        cmds.setAttr(startHandle[1]+'.rotateY', keyable=False)
        cmds.setAttr(startHandle[1]+'.rotateZ', keyable=False)
        cmds.setAttr(startHandle[1]+'.scaleX', keyable=False)
        cmds.setAttr(startHandle[1]+'.scaleY', keyable=False)
        cmds.setAttr(startHandle[1]+'.scaleZ', keyable=False)
        cmds.setAttr(startHandle[1]+'.visibility', keyable=False)
        newStartHandle = cmds.rename(startHandle[1], self.moduleNamespace+':splineStartHandleTransform')

        tempConstraint = cmds.pointConstraint(self.joints[0], newStartHandle, maintainOffset=False)
        cmds.delete(tempConstraint)
        cmds.pointConstraint(newStartHandle, startCluster[1], maintainOffset=True, name=startCluster[1]+'_parentConstraint')
        cmds.parent(newStartHandle, self.moduleHandleGrp, absolute=True)

        endHandle = objects.load_xhandleShape(self.moduleNamespace+'_endHandle', 10, True)
        cmds.setAttr(endHandle[0]+'.localScaleX', 0.35)
        cmds.setAttr(endHandle[0]+'.localScaleY', 0.35)
        cmds.setAttr(endHandle[0]+'.localScaleZ', 0.35)
        cmds.setAttr(endHandle[0]+'.drawStyle', 3)
        cmds.setAttr(endHandle[0]+'.wireframeThickness', 2)
        cmds.setAttr(endHandle[1]+'.rotateX', keyable=False)
        cmds.setAttr(endHandle[1]+'.rotateY', keyable=False)
        cmds.setAttr(endHandle[1]+'.rotateZ', keyable=False)
        cmds.setAttr(endHandle[1]+'.scaleX', keyable=False)
        cmds.setAttr(endHandle[1]+'.scaleY', keyable=False)
        cmds.setAttr(endHandle[1]+'.scaleZ', keyable=False)
        cmds.setAttr(endHandle[1]+'.visibility', keyable=False)
        newEndHandle = cmds.rename(endHandle[1], self.moduleNamespace+':splineEndHandleTransform')

        tempConstraint = cmds.pointConstraint(self.joints[-1], newEndHandle, maintainOffset=False)
        cmds.delete(tempConstraint)
        cmds.pointConstraint(newEndHandle, endCluster[1], maintainOffset=True, name=endCluster[1]+'_parentConstraint')
        cmds.parent(newEndHandle, self.moduleHandleGrp, absolute=True)

        splineAdjustCurveTransformList = []
        for (index, startWeight, endWeight) in [(0, 1, 0), (1, 0.66, 0.33), (2, 0.33, 0.66), (3, 0, 1)]:
            splineAdjustCurveTransforms = objects.createRawSplineAdjustCurveTransform(self.modHandleColour)
            cmds.setAttr(splineAdjustCurveTransforms[0]+'.scale', 0.8, 0.8, 0.8, type='double3')
            cmds.makeIdentity(splineAdjustCurveTransforms[0], scale=True, apply=True)
            newSplineAdjustCurvePreTransform = cmds.rename(splineAdjustCurveTransforms[0], self.moduleNamespace+':'+splineAdjustCurveTransforms[0].partition('_')[0]+'_'+str(index+1)+'_'+splineAdjustCurveTransforms[0].partition('_')[2])
            newSplineAdjustCurveTransform = cmds.rename(splineAdjustCurveTransforms[1], self.moduleNamespace+':'+splineAdjustCurveTransforms[1].partition('_')[0]+'_'+str(index+1)+'_'+splineAdjustCurveTransforms[1].partition('_')[2])
            splineAdjustCurveTransformList.append(newSplineAdjustCurveTransform)

            splineAdjustCurveCluster = cmds.cluster('%s.cv[%s]'%(newSplineNodeCurve, index), relative=True, name=newSplineAdjustCurveTransform+'_Cluster')
            cmds.setAttr(splineAdjustCurveCluster[1]+'.visibility', 0)
            collectedNodes.append(splineAdjustCurveCluster[0])

            tempConstraint = cmds.pointConstraint(splineAdjustCurveCluster[1], newSplineAdjustCurvePreTransform, maintainOffset=False)
            cmds.delete(tempConstraint)

            startPointConstraint = cmds.pointConstraint(newStartHandle, newSplineAdjustCurvePreTransform, maintainOffset=False, weight=startWeight, name=newSplineAdjustCurvePreTransform+'_startHandle_pointConstraint')
            endPointConstraint = cmds.pointConstraint(newEndHandle, newSplineAdjustCurvePreTransform, maintainOffset=False, weight=endWeight, name=newSplineAdjustCurvePreTransform+'_endHandle_pointConstraint')

            clusterGroup = cmds.group(splineAdjustCurveCluster[1], name=splineAdjustCurveCluster[1]+'_preTransform')
            cmds.parent(clusterGroup, newSplineAdjustCurvePreTransform, absolute=True)
            cmds.pointConstraint(newSplineAdjustCurveTransform, splineAdjustCurveCluster[1], maintainOffset=True, name=splineAdjustCurveCluster[1]+'_pointConstraint')

            cmds.parent(newSplineAdjustCurvePreTransform, self.moduleSplineAdjustCurveGrp, absolute=True)

            if index == 3:
                tangentConstraintTargetObject = newSplineAdjustCurveTransform

        worldReferenceTransform = cmds.createNode('transform', name=self.moduleNamespace+':orientationWorldReferenceTransform', parent=self.moduleOrientationRepresentationGrp)
        aimVector={'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[0]]
        upVector = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[1]]
        worldUpVector = {'XY':[0.0, 0.0, 1.0], 'YZ':[1.0, 0.0, 0.0], 'XZ':[0.0, 1.0, 0.0]}[self.onPlane]
        if self.mirrorModule and self.mirrorRotationFunc == 'Behaviour':
            aimVector = [i*-1 for i in aimVector]
        pairBlend_inputDriven = []
        for index in range(len(self.joints)):
            pairBlend = cmds.createNode('pairBlend', name=self.joints[index]+'_pairBlend', skipSelect=True)
            pairBlend_inputDriven.append(pairBlend)
            orientConstraint = cmds.orientConstraint(worldReferenceTransform, self.joints[index], maintainOffset=False, name=self.joints[index]+'_orientConstraint')[0]
            cmds.disconnectAttr(orientConstraint+'.constraintRotateX', self.joints[index]+'.rotateX')
            cmds.disconnectAttr(orientConstraint+'.constraintRotateY', self.joints[index]+'.rotateY')
            cmds.disconnectAttr(orientConstraint+'.constraintRotateZ', self.joints[index]+'.rotateZ')
            tangentConstraint = cmds.tangentConstraint(self.moduleNamespace+':splineNode_curve', self.joints[index], aimVector=aimVector, upVector=upVector, worldUpType='objectrotation', worldUpVector=worldUpVector, worldUpObject=tangentConstraintTargetObject, name=self.joints[index]+'_tangentConstraint')[0]
            cmds.disconnectAttr(tangentConstraint+'.constraintRotateX', self.joints[index]+'.rotateX')
            cmds.disconnectAttr(tangentConstraint+'.constraintRotateY', self.joints[index]+'.rotateY')
            cmds.disconnectAttr(tangentConstraint+'.constraintRotateZ', self.joints[index]+'.rotateZ')
            cmds.connectAttr(orientConstraint+'.constraintRotateX', pairBlend+'.inRotateX1')
            cmds.connectAttr(orientConstraint+'.constraintRotateY', pairBlend+'.inRotateY1')
            cmds.connectAttr(orientConstraint+'.constraintRotateZ', pairBlend+'.inRotateZ1')
            cmds.connectAttr(tangentConstraint+'.constraintRotateX', pairBlend+'.inRotateX2')
            cmds.connectAttr(tangentConstraint+'.constraintRotateY', pairBlend+'.inRotateY2')
            cmds.connectAttr(tangentConstraint+'.constraintRotateZ', pairBlend+'.inRotateZ2')
            cmds.connectAttr(pairBlend+'.outRotateX', self.joints[index]+'.rotateX')
            cmds.connectAttr(pairBlend+'.outRotateY', self.joints[index]+'.rotateY')
            cmds.connectAttr(pairBlend+'.outRotateZ', self.joints[index]+'.rotateZ')
            cmds.setAttr(pairBlend+'.rotateMode', 2)
        collectedNodes.extend(pairBlend_inputDriven)

        clusterNodes = cmds.listConnections(newSplineNodeCurve+'Shape', source=True, destination=True)
        for node in clusterNodes:
            if cmds.nodeType(node) == 'tweak':
                cmds.delete(node)
                break
        collectedNodes.append(self.moduleGrp)
        newRawLocaAxesInfoRepresentationTransforms = []
        for joint in self.joints:
            rawLocalAxesInfoRepresentationTransforms = objects.createRawLocalAxesInfoRepresentation()
            cmds.setAttr(rawLocalAxesInfoRepresentationTransforms[0]+'.scale', 0.8, 0.8, 0.8, type='double3')
            cmds.makeIdentity(rawLocalAxesInfoRepresentationTransforms[0], scale=True, apply=True)
            cmds.parent(rawLocalAxesInfoRepresentationTransforms[0], self.moduleOrientationRepresentationGrp)

            newRawLocaAxesInfoRepresentationPreTransform = cmds.rename(rawLocalAxesInfoRepresentationTransforms[0], joint+'_'+rawLocalAxesInfoRepresentationTransforms[0])
            newRawLocaAxesInfoRepresentationTransform = cmds.rename(rawLocalAxesInfoRepresentationTransforms[1], joint+'_'+rawLocalAxesInfoRepresentationTransforms[1])

            cmds.addAttr(newRawLocaAxesInfoRepresentationTransform, attributeType='enum', longName='tangent_Up_vector', enumName='Original:Reversed:', defaultValue=0, keyable=True)

            for (driver, driven) in ((1, -1), (0, 1)):
                cmds.setAttr(newRawLocaAxesInfoRepresentationTransform+'.tangent_Up_vector', driver)
                cmds.setAttr(joint+'_tangentConstraint.upVector'+self.nodeAxes[1].upper(), driven)
                cmds.setDrivenKeyframe(joint+'_tangentConstraint.upVector'+self.nodeAxes[1].upper(), currentDriver=newRawLocaAxesInfoRepresentationTransform+'.tangent_Up_vector')

            xhandle = objects.load_xhandleShape(joint, 2)
            cmds.setAttr(xhandle[0]+'.localScaleX', 0.09)
            cmds.setAttr(xhandle[0]+'.localScaleY', 0.09)
            cmds.setAttr(xhandle[0]+'.localScaleZ', 0.09)
            cmds.setAttr(xhandle[0]+'.ds', 5)

            cmds.pointConstraint(joint, newRawLocaAxesInfoRepresentationPreTransform, maintainOffset=False, name=newRawLocaAxesInfoRepresentationPreTransform+'_pointConstraint')
            cmds.orientConstraint(joint, newRawLocaAxesInfoRepresentationPreTransform, maintainOffset=False, name=newRawLocaAxesInfoRepresentationPreTransform+'_orientConstraint')

            newRawLocaAxesInfoRepresentationTransforms.append(newRawLocaAxesInfoRepresentationTransform)

        cmds.select(clear=True)

        collectedNodes += self.createHierarchySegmentForModuleParentingRepresentation()

        if self.proxyGeoStatus and self.proxyGeoElbow:
            self.createProxyGeo_elbows(self.proxyElbowType)

        mfunc.addNodesToContainer(self.moduleContainer, collectedNodes, includeHierarchyBelow=True, includeShapes=True)

        cmds.container(self.moduleContainer, edit=True, publishAndBind=[newStartHandle+'.translate', mfunc.stripMRTNamespace(newStartHandle)[1]+'_translate'])
        cmds.container(self.moduleContainer, edit=True, publishAndBind=[newEndHandle+'.translate', mfunc.stripMRTNamespace(newEndHandle)[1]+'_translate'])
        for transform in splineAdjustCurveTransformList:
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[transform+'.translate', mfunc.stripMRTNamespace(transform)[1]+'_translate'])

        self.addCustomAttributesOnModuleTransform()
        cmds.connectAttr(newStartHandle+'.Global_size', newStartHandle+'.scaleX')
        cmds.connectAttr(newStartHandle+'.Global_size', newStartHandle+'.scaleY')
        cmds.connectAttr(newStartHandle+'.Global_size', newStartHandle+'.scaleZ')
        cmds.connectAttr(newStartHandle+'.Global_size', newEndHandle+'.scaleX')
        cmds.connectAttr(newStartHandle+'.Global_size', newEndHandle+'.scaleY')
        cmds.connectAttr(newStartHandle+'.Global_size', newEndHandle+'.scaleZ')

        for i in range(1, 5):
            for j in ['X', 'Y', 'Z']:
                cmds.connectAttr(newStartHandle+'.Global_size', self.moduleNamespace+':spline_'+str(i)+'_adjustCurve_transform.scale'+str(j))
        for joint in self.joints:
            cmds.connectAttr(newStartHandle+'.Global_size', joint+'Shape.addScaleX')
            cmds.connectAttr(newStartHandle+'.Global_size', joint+'Shape.addScaleY')
            cmds.connectAttr(newStartHandle+'.Global_size', joint+'Shape.addScaleZ')
            cmds.connectAttr(newStartHandle+'.Global_size', joint+'_localAxesInfoRepresentation_preTransform.scaleX')
            cmds.connectAttr(newStartHandle+'.Global_size', joint+'_localAxesInfoRepresentation_preTransform.scaleY')
            cmds.connectAttr(newStartHandle+'.Global_size', joint+'_localAxesInfoRepresentation_preTransform.scaleZ')
            if self.proxyGeoStatus and self.proxyGeoElbow:
                cmds.connectAttr(newStartHandle+'.Global_size', joint+'_proxy_elbow_geo_scaleTransform.scaleX')
                cmds.connectAttr(newStartHandle+'.Global_size', joint+'_proxy_elbow_geo_scaleTransform.scaleY')
                cmds.connectAttr(newStartHandle+'.Global_size', joint+'_proxy_elbow_geo_scaleTransform.scaleZ')

        cmds.connectAttr(newStartHandle+'.Node_Orientation_Info', self.moduleOrientationRepresentationGrp+'.visibility')
        for transform in newRawLocaAxesInfoRepresentationTransforms:
            rotateAxis = self.nodeAxes[0]
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[transform+'.tangent_Up_vector', mfunc.stripMRTNamespace(transform)[1]+'_tangent_Up_Vector'])
            cmds.connectAttr(newStartHandle+'.Axis_Rotate', transform+'.rotate'+rotateAxis)
            cmds.connectAttr(newStartHandle+'.Node_Local_Orientation_Representation_Size', transform+'.scaleX')
            cmds.connectAttr(newStartHandle+'.Node_Local_Orientation_Representation_Size', transform+'.scaleY')
            cmds.connectAttr(newStartHandle+'.Node_Local_Orientation_Representation_Size', transform+'.scaleZ')

        cmds.setAttr(newStartHandle+'.Node_Local_Orientation_Representation_Size', 0.7)

        cmds.namespace(setNamespace=self.moduleNamespace)
        namespaceNodes = cmds.namespaceInfo(listOnlyDependencyNodes=True)
        animCurveNodes = cmds.ls(namespaceNodes, type='animCurve')
        mfunc.addNodesToContainer(self.moduleContainer, animCurveNodes)
        cmds.namespace(setNamespace=':')

        if not self.showOrientation:
            cmds.setAttr(newStartHandle+'.Node_Orientation_Info', 0)
        self.connectCustomOrientationReprToBoneProxies()
        #cmds.setAttr(newStartHandle+'.Global_size', 4)

    def checkPlaneAxisDirectionForIKhingeForOrientationRepresentation(self):
        offsetAxisVectorTransforms = {'XY':[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], 'YZ':[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]], 'XZ':[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]]}[self.onPlane]
        planeAxisOffset = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}
        IKhingePlaneAxisVectorTransforms = []
        tempLocatorForWorldTransformInfo_IKhingeOrientationVector = cmds.spaceLocator()[0]
        tempConstraint = cmds.parentConstraint(self.joints[1], tempLocatorForWorldTransformInfo_IKhingeOrientationVector, maintainOffset=False)
        cmds.delete(tempConstraint)
        cmds.parent(tempLocatorForWorldTransformInfo_IKhingeOrientationVector, self.joints[1])
        IKhingePlaneAxisVectorTransforms.append(cmds.xform(tempLocatorForWorldTransformInfo_IKhingeOrientationVector, query=True, worldSpace=True, translation=True))
        cmds.xform(tempLocatorForWorldTransformInfo_IKhingeOrientationVector, objectSpace=True, relative=True, translation=planeAxisOffset[self.nodeAxes[2]])
        IKhingePlaneAxisVectorTransforms.append(cmds.xform(tempLocatorForWorldTransformInfo_IKhingeOrientationVector, query=True, worldSpace=True, translation=True))
        cmds.delete(tempLocatorForWorldTransformInfo_IKhingeOrientationVector)

        direction_cosine = mfunc.returnDotProductDirection(offsetAxisVectorTransforms[0], offsetAxisVectorTransforms[1], IKhingePlaneAxisVectorTransforms[0], IKhingePlaneAxisVectorTransforms[1])[0]

        hingePreferredOrientationRepresentationAffectDueToIKRotation_directionCheck = {'XY':1.0, 'YZ':-1.0, 'XZ':1.0}[self.onPlane]

        if hingePreferredOrientationRepresentationAffectDueToIKRotation_directionCheck == direction_cosine:
            return True
        else:
            return False

    def createHingeNodeModule(self):
        #mfunc.forceSceneUpdate()
        mfunc.updateAllTransforms()
        # Set the current namespace to root.
        cmds.namespace(setNamespace=':')
        # Create a new namespace for the module.
        cmds.namespace(add=self.moduleNamespace)
        # Clear selection.
        cmds.select(clear=True)
        # Create the module container.
        moduleContainer = cmds.container(name=self.moduleContainer)
        # Create an empty group for containing module handle segments.
        self.moduleHandleSegmentGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleHandleSegmentCurveGrp')
        self.moduleParentRepresentationGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleParentRepresentationGrp')
        # Create an empty group for containing module hand hierarchy representations.
        self.moduleHierarchyRepresentationGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleHierarchyRepresentationGrp')
        # Create a module representation group containing the above two groups.
        self.moduleRepresentationGrp = cmds.group([self.moduleHandleSegmentGrp, self.moduleHierarchyRepresentationGrp, self.moduleParentRepresentationGrp], name=self.moduleNamespace+':moduleRepresentationObjGrp')
        # Create a module extras group.
        self.moduleExtrasGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleExtrasGrp')
        # Create a group under module extras to keep clusters for scaling node handle shapes.
        self.moduleNodeHandleShapeScaleClusterGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleNodeHandleShapeScaleClusterGrp', parent=self.moduleExtrasGrp)
        # Create a group under module extras to keep the IK segment aim nodes.
        self.moduleIKsegmentMidAimGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleIKsegmentMidAimGrp', parent=self.moduleExtrasGrp)
        # Create a group to contain the IK nodes and handles.
        self.moduleIKnodesGrp = cmds.group(empty=True, name=self.moduleNamespace+':moduleIKnodesGrp')
        # Create a main module group.
        self.moduleGrp = cmds.group([self.moduleRepresentationGrp, self.moduleExtrasGrp, self.moduleIKnodesGrp], name=self.moduleNamespace+':moduleGrp')

        # Add a custom attribute to the module group to store the number of nodes.
        cmds.addAttr(self.moduleGrp, attributeType='short', longName='numberOfNodes', defaultValue=self.numNodes, keyable=False)
        cmds.addAttr(self.moduleGrp, dataType='string', longName='nodeOrient', keyable=False)
        cmds.setAttr(self.moduleGrp+'.nodeOrient', self.nodeAxes, type='string')
        cmds.addAttr(self.moduleGrp, dataType='string', longName='moduleParent', keyable=False)
        cmds.setAttr(self.moduleGrp+'.moduleParent', 'None', type='string')
        cmds.addAttr(self.moduleGrp, dataType='string', longName='onPlane', keyable=False)
        cmds.setAttr(self.moduleGrp+'.onPlane', '+'+self.onPlane, type='string')
        cmds.addAttr(self.moduleGrp, dataType='string', longName='mirrorTranslation', keyable=False)
        cmds.setAttr(self.moduleGrp+'.mirrorTranslation', self.mirrorTranslationFunc, type='string')
        if self.mirrorModule:
            cmds.setAttr(self.moduleGrp+'.onPlane', '-'+self.onPlane, type='string')
        if self.mirrorModuleStatus == 'On':
            cmds.addAttr(self.moduleGrp, dataType='string', longName='mirrorModuleNamespace', keyable=False)
            cmds.setAttr(self.moduleGrp+'.mirrorModuleNamespace', self.mirror_moduleNamespace, type='string')
            cmds.addAttr(self.moduleGrp, dataType='string', longName='mirrorRotation', keyable=False)
            cmds.setAttr(self.moduleGrp+'.mirrorRotation', self.mirrorRotationFunc, type='string')
        # Create a group for proxy geometry.
        if self.proxyGeoStatus:
            if self.proxyGeoElbow or self.proxyGeoBones:
                self.proxyGeoGrp = cmds.group(empty=True, name=self.moduleNamespace+':proxyGeometryGrp')
                cmds.setAttr(self.proxyGeoGrp+'.overrideEnabled', 1)
                cmds.setAttr(self.proxyGeoGrp+'.overrideDisplayType', 2)
                if self.proxyGeoElbow:
                    cmds.addAttr(self.proxyGeoGrp, dataType='string', longName='elbowType', keyable=False)
                    cmds.setAttr(self.proxyGeoGrp+'.elbowType', self.proxyElbowType, type='string', lock=True)
                if self.mirrorModuleStatus == 'On':
                    cmds.addAttr(self.proxyGeoGrp, dataType='string', longName='mirrorInstance', keyable=False)
                    cmds.setAttr(self.proxyGeoGrp+'.mirrorInstance', self.proxyGeoMirrorInstance, type='string', lock=True)
        # Create a main module joints group, under the module group.
        self.moduleJointsGrp = cmds.group(empty=True, parent=self.moduleGrp, name=self.moduleNamespace+':moduleJointsGrp')
        # Initialize a list to contain created module node joints.
        self.joints = []
        # Get the positions of the module nodes, where the called method updates the self.initNodePos.
        self.returnNodeInfoTransformation(self.numNodes)
        # Move the joints group and the nodule IK nodes to the start position for the first joint node.
        cmds.xform(self.moduleJointsGrp, worldSpace=True, translation=self.initNodePos[0])
        cmds.xform(self.moduleIKnodesGrp, worldSpace=True, translation=self.initNodePos[0])

        containedNodes = []
        offset = self.moduleLen / 10.0
        hingeOffset = {'YZ':[offset, 0.0, 0.0], 'XZ':[0.0, offset, 0.0], 'XY':[0.0, 0.0, offset]}[self.onPlane]
        self.initNodePos[1] = map(lambda x,y: x+y, self.initNodePos[1], hingeOffset)

        # Create the module nodes (joints) by their position and name them accordingly.
        index = 0
        for nodePos in self.initNodePos:
            if index == 0:
                jointName = cmds.joint(name=self.moduleNamespace+':root_node_transform', position=nodePos, radius=0.0, scaleCompensate=False)
            elif nodePos == self.initNodePos[-1]:
                jointName = cmds.joint(name=self.moduleNamespace+':end_node_transform', position=nodePos, radius=0.0, scaleCompensate=False)
            else:
                jointName = cmds.joint(name=self.moduleNamespace+':node_%s_transform'%(index), position=nodePos, radius=0.0, scaleCompensate=False)
            cmds.setAttr(jointName+'.drawStyle', 2)
            self.joints.append(jointName)
            index += 1
        # Orient the joints.
        cmds.select(self.joints[0], replace=True)
        # For orientation we'll use the axis perpendicular to the creation plane as the up axis for secondary axis orient.
        secondAxisOrientation = {'XY':'z', 'YZ':'x', 'XZ':'y'}[self.onPlane] + 'up'
        cmds.joint(edit=True, orientJoint=self.nodeAxes.lower(), secondaryAxisOrient=secondAxisOrientation, zeroScaleOrient=True, children=True)

        if self.mirrorModule and self.mirrorRotationFunc == 'Behaviour':
            mirrorPlane = {'XY':False, 'YZ':False, 'XZ':False}
            mirrorPlane[self.onPlane] = True
            mirroredJoints = cmds.mirrorJoint(self.joints[0], mirrorXY=mirrorPlane['XY'], mirrorYZ=mirrorPlane['YZ'], mirrorXZ=mirrorPlane['XZ'], mirrorBehavior=True)
            cmds.delete(self.joints[0])
            self.joints = []
            for joint in mirroredJoints:
                newJoint = cmds.rename(joint, self.moduleNamespace+':'+joint)
                self.joints.append(newJoint)
        # Orient the end joint node.
        cmds.setAttr(self.joints[-1]+'.jointOrientX', 0)
        cmds.setAttr(self.joints[-1]+'.jointOrientY', 0)
        cmds.setAttr(self.joints[-1]+'.jointOrientZ', 0)
        # Clear selection after joint orientation.
        cmds.select(clear=True)

        ikNodes = cmds.ikHandle(startJoint=self.joints[0], endEffector=self.joints[-1], name=self.moduleNamespace+':rootToEndNode_ikHandle', solver='ikRPsolver')
        ikEffector = cmds.rename(ikNodes[1], self.moduleNamespace+':rootToEndNode_ikEffector')
        ikHandle = ikNodes[0]
        cmds.parent(ikHandle, self.moduleIKnodesGrp, absolute=True)
        cmds.setAttr(ikHandle + '.visibility', 0)

        cmds.xform(ikHandle, worldSpace=True, absolute=True, rotation=cmds.xform(self.joints[-1], query=True, worldSpace=True, absolute=True, rotation=True))

        ##rootHandle = objects.createRawHandle(self.modHandleColour)
        rootHandle = objects.createRawControlSurface(self.joints[0], self.modHandleColour, True)
        ##newRootHandle = cmds.rename(rootHandle[0], self.joints[0]+'_'+rootHandle[0])
        cmds.setAttr(rootHandle[0]+'.rotateX', keyable=False)
        cmds.setAttr(rootHandle[0]+'.rotateY', keyable=False)
        cmds.setAttr(rootHandle[0]+'.rotateZ', keyable=False)
        cmds.setAttr(rootHandle[0]+'.scaleX', keyable=False)
        cmds.setAttr(rootHandle[0]+'.scaleY', keyable=False)
        cmds.setAttr(rootHandle[0]+'.scaleZ', keyable=False)
        cmds.setAttr(rootHandle[0]+'.visibility', keyable=False)
        cmds.xform(rootHandle[0], worldSpace=True, absolute=True, translation=self.initNodePos[0])
        rootHandleConstraint = cmds.pointConstraint(rootHandle[0], self.joints[0], maintainOffset=False, name=self.joints[0]+'_pointConstraint')
        cmds.parent(rootHandle[0], self.moduleIKnodesGrp, absolute=True)

        ##elbowHandle = objects.createRawHandle(self.modHandleColour)
        elbowHandle = objects.createRawControlSurface(self.joints[1], self.modHandleColour, True)
        ##newElbowHandle = cmds.rename(elbowHandle[0], self.joints[1]+'_'+elbowHandle[0])
        cmds.setAttr(elbowHandle[0]+'.rotateX', keyable=False)
        cmds.setAttr(elbowHandle[0]+'.rotateY', keyable=False)
        cmds.setAttr(elbowHandle[0]+'.rotateZ', keyable=False)
        cmds.setAttr(elbowHandle[0]+'.scaleX', keyable=False)
        cmds.setAttr(elbowHandle[0]+'.scaleY', keyable=False)
        cmds.setAttr(elbowHandle[0]+'.scaleZ', keyable=False)
        cmds.setAttr(elbowHandle[0]+'.visibility', keyable=False)
        cmds.xform(elbowHandle[0], worldSpace=True, absolute=True, translation=self.initNodePos[1])
        elbowHandleConstraint = cmds.poleVectorConstraint(elbowHandle[0], ikHandle, name=ikHandle+'_poleVectorConstraint')
        cmds.parent(elbowHandle[0], self.moduleIKnodesGrp, absolute=True)

        ##endHandle = objects.createRawHandle(self.modHandleColour)
        endHandle = objects.createRawControlSurface(self.joints[-1], self.modHandleColour, True)
        ##newEndHandle = cmds.rename(endHandle[0], self.joints[-1]+'_'+endHandle[0])
        cmds.setAttr(endHandle[0]+'.rotateX', keyable=False)
        cmds.setAttr(endHandle[0]+'.rotateY', keyable=False)
        cmds.setAttr(endHandle[0]+'.rotateZ', keyable=False)
        cmds.setAttr(endHandle[0]+'.scaleX', keyable=False)
        cmds.setAttr(endHandle[0]+'.scaleY', keyable=False)
        cmds.setAttr(endHandle[0]+'.scaleZ', keyable=False)
        cmds.setAttr(endHandle[0]+'.visibility', keyable=False)
        cmds.xform(endHandle[0], worldSpace=True, absolute=True, translation=self.initNodePos[2])
        endHandleConstraint = cmds.pointConstraint(endHandle[0], ikHandle, maintainOffset=False, name=ikHandle+'_pointConstraint')
        cmds.parent(endHandle[0], self.moduleIKnodesGrp, absolute=True)

        for startPos, endPos, drivenJoint in [(rootHandle[0], elbowHandle[0], self.joints[1]), (elbowHandle[0], endHandle[0], self.joints[2])]:
            # Create a distance node to measure the distance between two joint handles, and connect the worldSpace translate values.
            segmentDistance = cmds.createNode('distanceBetween', name=drivenJoint+'_distanceNode')
            cmds.connectAttr(startPos+'.translate', segmentDistance+'.point1')
            cmds.connectAttr(endPos+'.translate', segmentDistance+'.point2')
            #
            distanceDivideFactor = cmds.createNode('multiplyDivide', name=drivenJoint+'_distanceDivideFactor')
            cmds.setAttr(distanceDivideFactor + '.operation', 2)
            aimAxis = self.nodeAxes[0]
            originalLength = cmds.getAttr(drivenJoint+'.translate'+aimAxis)
            cmds.connectAttr(segmentDistance+'.distance', distanceDivideFactor+'.input1'+aimAxis)
            cmds.setAttr(distanceDivideFactor+'.input2'+aimAxis, originalLength)

            drivenJointAimTranslateMultiply = cmds.createNode('multiplyDivide', name=drivenJoint+'_drivenJointAimTranslateMultiply')
            cmds.connectAttr(distanceDivideFactor+'.output'+aimAxis, drivenJointAimTranslateMultiply+'.input1'+aimAxis)
            cmds.setAttr(drivenJointAimTranslateMultiply+'.input2'+aimAxis, math.fabs(originalLength))
            cmds.connectAttr(drivenJointAimTranslateMultiply+'.output'+aimAxis, drivenJoint+'.translate'+aimAxis)
            containedNodes.extend([segmentDistance, distanceDivideFactor, drivenJointAimTranslateMultiply])
        mfunc.updateAllTransforms()
        #mfunc.forceSceneUpdate()
        i = 0
        for joint in self.joints:

            ##handleShape = joint+'_handleControlShape'
            handleShape = joint+'_controlShape'
            ##handleShapeScaleCluster = cmds.cluster(handleShape, relative=True, name=handleShape+'_handleShapeScaleCluster')
            handleShapeScaleCluster = cmds.cluster(handleShape, relative=True, name=handleShape+'_scaleCluster')
            cmds.parent(handleShapeScaleCluster[1], self.moduleNodeHandleShapeScaleClusterGrp, absolute=True)
            cmds.setAttr(handleShapeScaleCluster[1]+'.visibility', 0)
            # Collect the cluster nodes.
            clusterNodes = cmds.listConnections(handleShape, source=True, destination=True)
            # Remove the tweak node.
            for node in clusterNodes:
                if cmds.nodeType(node) == 'tweak':
                    cmds.delete(node)
                    break
            # Update the cluster node list.
            clusterNodes = cmds.listConnections(handleShape, source=True, destination=True)
            containedNodes.extend(clusterNodes)

            worldPosLocator = cmds.spaceLocator(name=joint+'_worldPosLocator')[0]
            cmds.setAttr(worldPosLocator + '.visibility', 0)
            worldPosLocator_constraint = cmds.pointConstraint(joint, worldPosLocator, maintainOffset=False, name=self.moduleNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_worldPosLocator_pointConstraint')
            cmds.parent(worldPosLocator, self.moduleHandleSegmentGrp, absolute=True)
            i += 1

        j = 0
        for joint in self.joints:
            if joint == self.joints[-1]:
                break
            #handleSegmentParts = objects.createRawHandleSegment(self.modHandleColour)
            handleSegmentParts = objects.createRawSegmentCurve(self.modHandleColour)
            extra_nodes = []
            for node in handleSegmentParts[4]:
                if cmds.objExists(node):
                    extra_nodes.append(cmds.rename(node, self.moduleNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_clusterParts_'+node))
            containedNodes.extend(extra_nodes)

            startClosestPointOnSurface = cmds.createNode('closestPointOnSurface', name=joint+'_'+handleSegmentParts[5]+'_closestPointOnSurface')
            ##cmds.connectAttr(joint+'_handleControlShape.worldSpace[0]', startClosestPointOnSurface+'.inputSurface')
            cmds.connectAttr(joint+'_controlShape.worldSpace[0]', startClosestPointOnSurface+'.inputSurface')
            cmds.connectAttr(self.joints[j+1]+'_worldPosLocator.translate', startClosestPointOnSurface+'.inPosition')
            cmds.connectAttr(startClosestPointOnSurface+'.position', handleSegmentParts[5]+'.translate')
            endClosestPointOnSurface = cmds.createNode('closestPointOnSurface', name=self.joints[j+1]+'_'+handleSegmentParts[6]+'_closestPointOnSurface')
            ##cmds.connectAttr(self.joints[j+1]+'_handleControlShape.worldSpace[0]', endClosestPointOnSurface+'.inputSurface')
            cmds.connectAttr(self.joints[j+1]+'_controlShape.worldSpace[0]', endClosestPointOnSurface+'.inputSurface')
            cmds.connectAttr(joint+'_worldPosLocator.translate', endClosestPointOnSurface+'.inPosition')
            cmds.connectAttr(endClosestPointOnSurface+'.position', handleSegmentParts[6]+'.translate')

            cmds.parent([handleSegmentParts[1], handleSegmentParts[2][1], handleSegmentParts[3][1], handleSegmentParts[5], handleSegmentParts[6]], self.moduleHandleSegmentGrp, absolute=True)

            cmds.rename(handleSegmentParts[1], self.moduleNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_'+handleSegmentParts[1])

            newStartLocator = cmds.rename(handleSegmentParts[5], joint+'_'+handleSegmentParts[5])
            newEndLocator = cmds.rename(handleSegmentParts[6], self.joints[j+1]+'_'+handleSegmentParts[6])

            newStartClusterHandle = cmds.rename(handleSegmentParts[2][1], self.moduleNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_'+handleSegmentParts[2][1])
            newEndClusterHandle = cmds.rename(handleSegmentParts[3][1], self.moduleNamespace+':'+mfunc.stripMRTNamespace(self.joints[j+1])[1]+'_'+handleSegmentParts[3][1])
            cmds.rename(newStartClusterHandle+'|'+handleSegmentParts[7].rpartition('|')[2], joint+'_'+handleSegmentParts[7].rpartition('|')[2])
            cmds.rename(newEndClusterHandle+'|'+handleSegmentParts[8].rpartition('|')[2], self.joints[j+1]+'_'+handleSegmentParts[8].rpartition('|')[2])
            ##startClusterGrpParts = cmds.rename('handleControlSegmentCurve_StartClusterGroupParts', newStartClusterHandle+'_ClusterGroupParts')
            ##endClusterGrpParts = cmds.rename('handleControlSegmentCurve_EndClusterGroupParts', newEndClusterHandle+'_ClusterGroupParts')
            startClusterGrpParts = cmds.rename('segmentCurve_startClusterGroupParts', newStartClusterHandle+'_clusterGroupParts')
            endClusterGrpParts = cmds.rename('segmentCurve_endClusterGroupParts', newEndClusterHandle+'_clusterGroupParts')



            ##arclen = cmds.arclen(joint+'_handleControlSegmentCurve', constructionHistory=True)
            ##namedArclen = cmds.rename(arclen, joint+'_handleControlSegmentCurve_curveInfo')
            arclen = cmds.arclen(joint+'_segmentCurve', constructionHistory=True)
            namedArclen = cmds.rename(arclen, joint+'_segmentCurve_curveInfo')

            cmds.select(clear=True)
            containedNodes.extend([newStartClusterHandle, newEndClusterHandle, newStartClusterHandle+'Cluster', newEndClusterHandle+'Cluster', startClosestPointOnSurface, endClosestPointOnSurface, namedArclen, startClusterGrpParts, endClusterGrpParts])
            j += 1

        #rootEndHandleSegmentParts = objects.createRawHandleSegment(3)
        rootEndHandleSegmentParts = objects.createRawSegmentCurve(3)
        #cmds.setAttr(rootEndHandleSegmentParts[0]+'.overrideEnabled', 1)
        #cmds.setAttr(rootEndHandleSegmentParts[0]+'.overrideColor', 3)
        extra_nodes = []
        for node in rootEndHandleSegmentParts[4]:
            if cmds.objExists(node):
                extra_nodes.append(cmds.rename(node, self.moduleNamespace+':'+'rootEndHandleIKsegment_clusterParts_'+node))
        containedNodes.extend(extra_nodes)

        startClosestPointOnSurface = cmds.createNode('closestPointOnSurface', name=self.moduleNamespace+':startHandleIKsegment_'+rootEndHandleSegmentParts[5]+'_closestPointOnSurface')
        ##cmds.connectAttr(self.joints[0]+'_handleControlShape.worldSpace[0]', startClosestPointOnSurface+'.inputSurface')
        cmds.connectAttr(self.joints[0]+'_controlShape.worldSpace[0]', startClosestPointOnSurface+'.inputSurface')
        cmds.connectAttr(self.joints[-1]+'_worldPosLocator.translate', startClosestPointOnSurface+'.inPosition')
        cmds.connectAttr(startClosestPointOnSurface+'.position', rootEndHandleSegmentParts[5]+'.translate')
        endClosestPointOnSurface = cmds.createNode('closestPointOnSurface', name=self.moduleNamespace+':endHandleIKsegment_'+rootEndHandleSegmentParts[6]+'_closestPointOnSurface')
        ##cmds.connectAttr(self.joints[-1]+'_handleControlShape.worldSpace[0]', endClosestPointOnSurface+'.inputSurface')
        cmds.connectAttr(self.joints[-1]+'_controlShape.worldSpace[0]', endClosestPointOnSurface+'.inputSurface')
        cmds.connectAttr(self.joints[0]+'_worldPosLocator.translate', endClosestPointOnSurface+'.inPosition')
        cmds.connectAttr(endClosestPointOnSurface+'.position', rootEndHandleSegmentParts[6]+'.translate')

        cmds.parent([rootEndHandleSegmentParts[1], rootEndHandleSegmentParts[2][1], rootEndHandleSegmentParts[3][1], rootEndHandleSegmentParts[5], rootEndHandleSegmentParts[6]], self.moduleHandleSegmentGrp, absolute=True)

        rootEndHandleIKsegmentCurve = cmds.rename(rootEndHandleSegmentParts[1], self.moduleNamespace+':rootEndHandleIKsegment_'+rootEndHandleSegmentParts[1])

        newStartLocator = cmds.rename(rootEndHandleSegmentParts[5], self.moduleNamespace+':startHandleIKsegment_'+rootEndHandleSegmentParts[5])
        newEndLocator = cmds.rename(rootEndHandleSegmentParts[6], self.moduleNamespace+':endHandleIKsegment_'+rootEndHandleSegmentParts[6])

        newStartClusterHandle = cmds.rename(rootEndHandleSegmentParts[2][1], self.moduleNamespace+':startHandleIKsegment_'+rootEndHandleSegmentParts[2][1])
        newEndClusterHandle = cmds.rename(rootEndHandleSegmentParts[3][1], self.moduleNamespace+':endHandleIKsegment_'+rootEndHandleSegmentParts[3][1])
        cmds.rename(newStartClusterHandle+'|'+rootEndHandleSegmentParts[7].rpartition('|')[2], self.moduleNamespace+':startHandleIKsegment_'+rootEndHandleSegmentParts[7].rpartition('|')[2])
        cmds.rename(newEndClusterHandle + '|'+rootEndHandleSegmentParts[8].rpartition('|')[2], self.moduleNamespace+':endHandleIKsegment_'+rootEndHandleSegmentParts[8].rpartition('|')[2])
        #startClusterGrpParts = cmds.rename('handleControlSegmentCurve_StartClusterGroupParts', newStartClusterHandle+'_ClusterGroupParts')
        #endClusterGrpParts = cmds.rename('handleControlSegmentCurve_EndClusterGroupParts', newEndClusterHandle+'_ClusterGroupParts')
        startClusterGrpParts = cmds.rename('segmentCurve_startClusterGroupParts', newStartClusterHandle+'_clusterGroupParts')
        endClusterGrpParts = cmds.rename('segmentCurve_endClusterGroupParts', newEndClusterHandle+'_clusterGroupParts')

        cmds.select(clear=True)

        containedNodes.extend([newStartClusterHandle, newEndClusterHandle, newStartClusterHandle+'Cluster', newEndClusterHandle+'Cluster', startClosestPointOnSurface, endClosestPointOnSurface, startClusterGrpParts, endClusterGrpParts])

        rootEndHandleIKsegmentMidLocator = cmds.spaceLocator(name=self.moduleNamespace+':rootEndHandleIKsegmentMidLocator')[0]
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'.translateX', keyable=False)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'.translateY', keyable=False)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'.translateZ', keyable=False)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'.rotateX', keyable=False)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'.rotateY', keyable=False)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'.rotateZ', keyable=False)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'.scaleX', keyable=False)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'.scaleY', keyable=False)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'.scaleZ', keyable=False)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'.visibility', keyable=False)

        cmds.parent(rootEndHandleIKsegmentMidLocator, self.moduleIKsegmentMidAimGrp, absolute=True)
        rootEndHandleIKsegmentMidLocator_pointOnCurveInfo = cmds.createNode('pointOnCurveInfo', name=self.moduleNamespace+':rootEndHandleIKsegmentCurveMidLocator_pointOnCurveInfo')
        cmds.connectAttr(rootEndHandleIKsegmentCurve+'Shape.worldSpace[0]', rootEndHandleIKsegmentMidLocator_pointOnCurveInfo+'.inputCurve')
        cmds.setAttr(rootEndHandleIKsegmentMidLocator_pointOnCurveInfo+'.turnOnPercentage', True)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator_pointOnCurveInfo+'.parameter', 0.5)
        cmds.connectAttr(rootEndHandleIKsegmentMidLocator_pointOnCurveInfo+'.position', rootEndHandleIKsegmentMidLocator+'.translate')
        containedNodes.append(rootEndHandleIKsegmentMidLocator_pointOnCurveInfo)

        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'Shape.localScaleX', 0.1)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'Shape.localScaleY', 0)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'Shape.localScaleZ', 0.1)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'Shape.overrideEnabled', 1)
        cmds.setAttr(rootEndHandleIKsegmentMidLocator+'Shape.overrideColor', 2)

        ikSegmentAimStartLocator = cmds.spaceLocator(name=self.moduleNamespace+':ikSegmentAimStartLocator')[0]
        cmds.setAttr(ikSegmentAimStartLocator+'.visibility', 0)
        cmds.parent(ikSegmentAimStartLocator, self.moduleIKsegmentMidAimGrp, absolute=True)

        ikSegmentAimEndLocator = cmds.spaceLocator(name=self.moduleNamespace+':ikSegmentAimEndLocator')[0]
        cmds.setAttr(ikSegmentAimEndLocator+'.visibility', 0)
        cmds.parent(ikSegmentAimEndLocator, self.moduleIKsegmentMidAimGrp, absolute=True)

        cmds.geometryConstraint(rootEndHandleIKsegmentCurve, ikSegmentAimStartLocator, name=ikSegmentAimStartLocator+'_geoConstraint')
        #cmds.pointConstraint(self.joints[1]+'_handleControl', ikSegmentAimStartLocator, maintainOffset=False, name=ikSegmentAimStartLocator+'_pointConstraint')
        cmds.pointConstraint(self.joints[1]+'_control', ikSegmentAimStartLocator, maintainOffset=False, name=ikSegmentAimStartLocator+'_pointConstraint')
        ikSegmentAimStartClosestPointOnSurface = cmds.createNode('closestPointOnSurface', name=self.moduleNamespace+':ikSegmentAimClosestPointOnSurface')
        ##cmds.connectAttr(self.joints[1]+'_handleControlShape.worldSpace[0]', ikSegmentAimStartClosestPointOnSurface+'.inputSurface')
        cmds.connectAttr(self.joints[1]+'_controlShape.worldSpace[0]', ikSegmentAimStartClosestPointOnSurface+'.inputSurface')
        cmds.connectAttr(ikSegmentAimStartLocator+'Shape.worldPosition[0]', ikSegmentAimStartClosestPointOnSurface+'.inPosition')
        cmds.connectAttr(ikSegmentAimStartClosestPointOnSurface+'.position', ikSegmentAimEndLocator+'.translate')
        containedNodes.append(ikSegmentAimStartClosestPointOnSurface)

        ikSegmentAimCurve = cmds.createNode('transform', name=self.moduleNamespace+':ikSegmentAimCurve')
        cmds.setAttr(ikSegmentAimCurve+'.translateX', keyable=False)
        cmds.setAttr(ikSegmentAimCurve+'.translateY', keyable=False)
        cmds.setAttr(ikSegmentAimCurve+'.translateZ', keyable=False)
        cmds.setAttr(ikSegmentAimCurve+'.rotateX', keyable=False)
        cmds.setAttr(ikSegmentAimCurve+'.rotateY', keyable=False)
        cmds.setAttr(ikSegmentAimCurve+'.rotateZ', keyable=False)
        cmds.setAttr(ikSegmentAimCurve+'.scaleX', keyable=False)
        cmds.setAttr(ikSegmentAimCurve+'.scaleY', keyable=False)
        cmds.setAttr(ikSegmentAimCurve+'.scaleZ', keyable=False)
        cmds.setAttr(ikSegmentAimCurve+'.visibility', keyable=False)
        cmds.createNode('nurbsCurve', name=self.moduleNamespace+':ikSegmentAimCurveShape', parent=ikSegmentAimCurve)
        cmds.setAttr('.overrideEnabled', 1)
        cmds.setAttr('.overrideColor', 2)
        mel.eval('''setAttr ".cached" -type "nurbsCurve"
        1 1 0 no 3
        2 0 1
        2
        0 0 0
        1 0 0;''')
        cmds.parent(ikSegmentAimCurve, self.moduleIKsegmentMidAimGrp, absolute=True)

        cmds.pointConstraint(ikSegmentAimStartLocator, ikSegmentAimCurve, maintainOffset=False, name=ikSegmentAimCurve+'_pointConstraint')
        cmds.aimConstraint(ikSegmentAimEndLocator, ikSegmentAimCurve, maintainOffset=False, aimVector=[1.0, 0.0, 0.0], upVector=[0.0, 1.0, 0.0], worldUpType='scene', name=ikSegmentAimCurve+'_aimConstraint')

        rootEndHandleIKsegmentMidLocatorAimConstraint = cmds.aimConstraint(self.joints[-1], rootEndHandleIKsegmentMidLocator, maintainOffset=False, aimVector=[0.0, 1.0, 0.0], upVector=[0.0, 0.0, 1.0], worldUpType='object', worldUpObject=ikSegmentAimEndLocator, name=rootEndHandleIKsegmentMidLocator+'_aimConstraint')[0]
        cmds.setAttr(rootEndHandleIKsegmentMidLocatorAimConstraint+'.offsetY', 45)

        ikSegmentAimCurveLength_distance = cmds.createNode('distanceBetween', name=self.moduleNamespace+':ikSegmentAimCurveLength_distanceNode')
        cmds.connectAttr(ikSegmentAimStartLocator+'Shape.worldPosition[0]', ikSegmentAimCurveLength_distance+'.point1')
        cmds.connectAttr(ikSegmentAimEndLocator+'Shape.worldPosition[0]', ikSegmentAimCurveLength_distance+'.point2')
        cmds.connectAttr(ikSegmentAimCurveLength_distance+'.distance', ikSegmentAimCurve+'.scaleX')
        containedNodes.append(ikSegmentAimCurveLength_distance)

        # Add the module transform to the module, at the position of the root node.
        moduleTransform = objects.load_xhandleShape(self.moduleNamespace+'_handle', 24, True)
        cmds.setAttr(moduleTransform[0]+'.localScaleX', 0.26)
        cmds.setAttr(moduleTransform[0]+'.localScaleY', 0.26)
        cmds.setAttr(moduleTransform[0]+'.localScaleZ', 0.26)
        cmds.setAttr(moduleTransform[0]+'.drawStyle', 8)
        cmds.setAttr(moduleTransform[0]+'.drawOrtho', 0)
        cmds.setAttr(moduleTransform[0]+'.wireframeThickness', 2)
        cmds.setAttr(moduleTransform[1]+'.scaleX', keyable=False)
        cmds.setAttr(moduleTransform[1]+'.scaleY', keyable=False)
        cmds.setAttr(moduleTransform[1]+'.scaleZ', keyable=False)
        cmds.setAttr(moduleTransform[1]+'.visibility', keyable=False)
        cmds.addAttr(moduleTransform[1], attributeType='float', longName='globalScale', hasMinValue=True, minValue=0, defaultValue=1, keyable=True)
        self.moduleTransform = cmds.rename(moduleTransform[1], self.moduleNamespace+':module_transform')
        tempConstraint = cmds.pointConstraint(self.joints[0], self.moduleTransform, maintainOffset=False)
        cmds.delete(tempConstraint)

        cmds.parent(self.moduleTransform, self.moduleGrp, absolute=True)
        cmds.parentConstraint(self.moduleTransform, self.moduleIKnodesGrp, maintainOffset=True, name=self.moduleTransform+'_parentConstraint')
        cmds.scaleConstraint(self.moduleTransform, self.moduleIKnodesGrp, maintainOffset=False, name=self.moduleTransform+'_scaleConstraint')
        cmds.scaleConstraint(self.moduleTransform, self.moduleJointsGrp, maintainOffset=False, name=self.moduleTransform+'_scaleConstraint')
        cmds.scaleConstraint(self.moduleTransform, rootEndHandleIKsegmentMidLocator, maintainOffset=False, name=self.moduleTransform+'_scaleConstraint')

        # Connect the scale attributes to an aliased 'globalScale' attribute (This could've been done on the raw def itself, but it was issuing a cycle; not sure why. But the DG eval was not cyclic).
        cmds.connectAttr(self.moduleTransform+'.globalScale', self.moduleTransform+'.scaleX')
        cmds.connectAttr(self.moduleTransform+'.globalScale', self.moduleTransform+'.scaleY')
        cmds.connectAttr(self.moduleTransform+'.globalScale', self.moduleTransform+'.scaleZ')

        # Connect the globalScale attribute of the module transform to the xhandleShape(s).
        #for handle in [rootHandle[0], elbowHandle[0], endHandle[0]]:
            #xhandle = objects.load_xhandleShape(handle, self.modHandleColour)
            #cmds.setAttr(xhandle[0]+'.localScaleX', 0.145)
            #cmds.setAttr(xhandle[0]+'.localScaleY', 0.145)
            #cmds.setAttr(xhandle[0]+'.localScaleZ', 0.145)
            ##cmds.parent(xhandle[0], handle, shape=True, relative=True)
            ##cmds.delete(xhandle[1])
            #cmds.setAttr(xhandle[0]+'.ds', 5)
            #cmds.setAttr(handle+'Shape.visibility', 0)

        for handle in [rootHandle[0], elbowHandle[0], endHandle[0]]:
            xhandle = objects.load_xhandleShape(handle+'X', self.modHandleColour, True)
            cmds.setAttr(xhandle[0]+'.localScaleX', 0.089)
            cmds.setAttr(xhandle[0]+'.localScaleY', 0.089)
            cmds.setAttr(xhandle[0]+'.localScaleZ', 0.089)
            cmds.parent(xhandle[0], handle, shape=True, relative=True)
            cmds.delete(xhandle[1])
            cmds.setAttr(xhandle[0]+'.ds', 5)
            cmds.setAttr(handle+'Shape.visibility', 0)

        hingeAxisRepresentation = objects.createRawIKhingeAxisRepresenation(self.nodeAxes[1:])
        cmds.setAttr(hingeAxisRepresentation+'.scale', 2.3, 2.3, 2.3, type='double3')
        cmds.makeIdentity(hingeAxisRepresentation, scale=True, apply=True)
        hingeAxisRepresentation = cmds.rename(hingeAxisRepresentation, self.joints[1]+'_'+hingeAxisRepresentation)
        cmds.parent(hingeAxisRepresentation, self.moduleRepresentationGrp, absolute=True)
        cmds.parentConstraint(self.joints[1], hingeAxisRepresentation, maintainOffset=False, name=hingeAxisRepresentation+'_parentConstraint')
        cmds.scaleConstraint(self.moduleTransform, hingeAxisRepresentation, maintainOffset=False, name=self.moduleTransform+'_scaleConstraint')

        ikPreferredRotationRepresentaton = objects.createRawIKPreferredRotationRepresentation(self.nodeAxes[2])
        cmds.setAttr(ikPreferredRotationRepresentaton+'.scale', 0.6, 0.6, 0.6, type='double3')
        cmds.makeIdentity(ikPreferredRotationRepresentaton, scale=True, apply=True)
        ikPreferredRotationRepresentaton = cmds.rename(ikPreferredRotationRepresentaton, self.moduleNamespace+':'+ikPreferredRotationRepresentaton)
        cmds.parent(ikPreferredRotationRepresentaton, self.moduleRepresentationGrp, absolute=True)
        cmds.pointConstraint(self.moduleNamespace+':rootEndHandleIKsegmentMidLocator', ikPreferredRotationRepresentaton, maintainOffset=False, name=ikPreferredRotationRepresentaton+'_pointConstraint')
        cmds.scaleConstraint(self.moduleTransform, ikPreferredRotationRepresentaton, maintainOffset=False, name=self.moduleTransform+'_ikPreferredRotRepr_scaleConstraint')
        orientConstraint = cmds.orientConstraint(self.moduleNamespace+':rootEndHandleIKsegmentMidLocator', ikPreferredRotationRepresentaton, maintainOffset=False, name=ikPreferredRotationRepresentaton+'_orientConstraint')[0]
        cmds.setAttr(orientConstraint+'.offsetY', -45)
        #modifyIKhingePreferredOrientationRepresentation = self.checkPlaneAxisDirectionForIKhingeForOrientationRepresentation()
        #if modifyIKhingePreferredOrientationRepresentation and self.mirrorRotationFunc == 'Behaviour':
            #scaleAxisApply = {'X':[-1.0, 1.0, 1.0], 'Y':[1.0, -1.0, 1.0], 'Z':[1.0, 1.0, -1.0]}[self.nodeAxes[1]]
            #cmds.select(['{0}_hingeRotate_Shape.cv[{1}]'.format(hingeOrientationRepresentation, cv) for cv in range(41)])
            #cmds.xform(scale=scaleAxisApply, absolute=True)
            #cmds.select(clear=True)

        index = 0
        for joint in self.joints[:-1]:

            hierarchyRepresentation = objects.createRawHierarchyRepresentation(self.nodeAxes[0])

            ##startLocator = joint + '_handleControlSegmentCurve_startLocator'
            ##endLocator = self.joints[index+1] + '_handleControlSegmentCurve_endLocator'
            startLocator = joint + '_segmentCurve_startLocator'
            endLocator = self.joints[index+1] + '_segmentCurve_endLocator'
            cmds.pointConstraint(startLocator, endLocator, hierarchyRepresentation, maintainOffset=False, name=joint+'_hierarchy_representation_pointConstraint')
            cmds.scaleConstraint(joint, hierarchyRepresentation, maintainOffset=False, name=joint+'_hierarchy_representation_scaleConstraint')

            aimVector = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[0]]
            upVector = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[1]]
            cmds.aimConstraint(self.joints[index+1], hierarchyRepresentation, maintainOffset=False, aimVector=aimVector, upVector=upVector, worldUpVector=upVector, worldUpType='objectRotation', worldUpObject=joint, name=self.moduleNamespace+':'+mfunc.stripMRTNamespace(self.joints[index+1])[1]+'_hierarchy_representation_aimConstraint')

            cmds.parent(hierarchyRepresentation, self.moduleHierarchyRepresentationGrp, absolute=True)

            cmds.rename(hierarchyRepresentation, joint+'_'+hierarchyRepresentation)
            index += 1

        cmds.select(clear=True)

        containedNodes += self.createHierarchySegmentForModuleParentingRepresentation()

        if self.proxyGeoStatus:
            if self.proxyGeoElbow:
                self.createProxyGeo_elbows(self.proxyElbowType)
            if self.proxyGeoBones:
                self.createProxyGeo_bones()

        # Add the module group to the contained nodes list.
        containedNodes += [self.moduleGrp]
        # Add the contained nodes to the module container.
        mfunc.addNodesToContainer(self.moduleContainer, containedNodes, includeHierarchyBelow=True, includeShapes=True)

        moduleTransformName = mfunc.stripMRTNamespace(self.moduleTransform)[1]
        cmds.container(self.moduleContainer, edit=True, publishAndBind=[self.moduleTransform+'.translate', moduleTransformName+'_translate'])
        cmds.container(self.moduleContainer, edit=True, publishAndBind=[self.moduleTransform+'.rotate', moduleTransformName+'_rotate'])
        cmds.container(self.moduleContainer, edit=True, publishAndBind=[self.moduleTransform+'.globalScale', moduleTransformName+'_globalScale'])

        for handle in (rootHandle[0], elbowHandle[0], endHandle[0]):
            handleName = mfunc.stripMRTNamespace(handle)[1]
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[handle+'.translate', handleName+'_translate'])

        for joint in self.joints:
            jointName = mfunc.stripMRTNamespace(joint)[1]
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[joint+'.rotate', jointName+'_rotate'])

        self.addCustomAttributesOnModuleTransform()
        if self.onPlane == 'XZ':
            offset = cmds.getAttr(self.moduleNamespace+':node_1_transform_control.translateY')
            cmds.setAttr(self.moduleNamespace+':node_1_transform_control.translateY', 0)
            cmds.setAttr(self.moduleNamespace+':node_1_transform_control.translateZ', offset)
        if self.onPlane == 'XY' and self.mirrorModule:
            ##offset = cmds.getAttr(self.moduleNamespace+':node_1_transform_handleControl.translateZ')
            ##cmds.setAttr(self.moduleNamespace+':node_1_transform_handleControl.translateZ', offset*-1)
            offset = cmds.getAttr(self.moduleNamespace+':node_1_transform_control.translateZ')
            cmds.setAttr(self.moduleNamespace+':node_1_transform_control.translateZ', offset*-1)
        if self.onPlane == 'YZ' and self.mirrorModule:
            ##offset = cmds.getAttr(self.moduleNamespace+':node_1_transform_handleControl.translateX')
            ##cmds.setAttr(self.moduleNamespace+':node_1_transform_handleControl.translateX', offset*-1)
            offset = cmds.getAttr(self.moduleNamespace+':node_1_transform_control.translateX')
            cmds.setAttr(self.moduleNamespace+':node_1_transform_control.translateX', offset*-1)

        ##mfunc.forceSceneUpdate()
        #cmds.setAttr(self.moduleTransform+'.globalScale', 4)

    def addCustomAttributesOnModuleTransform(self):
        if self.moduleName == 'JointNode':

            moduleNode = '|' + self.moduleGrp + '|' + self.moduleTransform

            if len(self.joints) > 1:
                cmds.addAttr(moduleNode, attributeType='enum', longName='Node_Orientation_Representation_Toggle', enumName='----------------------------:', keyable=True)
                for joint in self.joints[:-1]:
                    longName = mfunc.stripMRTNamespace(joint)[1]+'_orientation_representation_transform'
                    cmds.addAttr(moduleNode, attributeType='enum', longName=longName, enumName='Off:On:', defaultValue=1, keyable=True)
                    cmds.connectAttr(moduleNode+'.'+longName, joint+'_orientation_representation_transform.visibility')
                    if not self.showOrientation:
                        cmds.setAttr(moduleNode+'.'+longName, 0)
                    cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.'+longName, 'module_transform_'+longName+'_toggle'])

                cmds.addAttr(moduleNode, attributeType='enum', longName='Node_Hierarchy_Representation_Toggle', enumName='----------------------------:', keyable=True)
                for joint in self.joints[:-1]:
                    longName = mfunc.stripMRTNamespace(joint)[1]+'_hierarchy_representation'
                    cmds.addAttr(moduleNode, attributeType='enum', longName=longName, enumName='Off:On:', defaultValue=1, keyable=True)
                    cmds.connectAttr(moduleNode+'.'+longName, joint+'_hierarchy_representation.visibility')
                    ##cmds.connectAttr(moduleNode+'.'+longName, joint+'_handleControlSegmentCurve.visibility')
                    cmds.connectAttr(moduleNode+'.'+longName, joint+'_segmentCurve.visibility')
                    if not self.showHierarchy:
                        cmds.setAttr(moduleNode+'.'+longName, 0)
                    cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.'+longName, 'module_transform_'+longName+'_toggle'])

            if len(self.joints) == 1:
                cmds.addAttr(moduleNode, attributeType='enum', longName='Node_Orientation_Representation_Toggle', enumName='----------------------------:', keyable=True)
                longName = mfunc.stripMRTNamespace(self.joints[0])[1]+'_single_orientation_representation_transform'
                cmds.addAttr(moduleNode, attributeType='enum', longName=longName, enumName='Off:On:', defaultValue=1, keyable=True)
                cmds.connectAttr(moduleNode+'.'+longName, mfunc.stripMRTNamespace(self.joints[0])[0]+':single_orientation_representation_transform.visibility')
                if not self.showOrientation:
                    cmds.setAttr(moduleNode+'.'+longName, 0)
                cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.'+longName, 'module_transform_'+longName+'_toggle'])

            cmds.addAttr(moduleNode, attributeType='enum', longName='Node_Handle_Size', enumName='---------------------------:', keyable=True)
            for joint in self.joints:
                longName = mfunc.stripMRTNamespace(joint)[1]+'_handle_size'
                cmds.addAttr(moduleNode, attributeType='float', longName=longName, hasMinValue=True, minValue=0, defaultValue=1, keyable=True)
                cmds.connectAttr(moduleNode+'.'+longName, joint+'_controlShape_scaleClusterHandle.scaleX')
                cmds.connectAttr(moduleNode+'.'+longName, joint+'_controlShape_scaleClusterHandle.scaleY')
                cmds.connectAttr(moduleNode+'.'+longName, joint+'_controlShape_scaleClusterHandle.scaleZ')
                cmds.connectAttr(moduleNode+'.'+longName, joint+'Shape.addScaleX')
                cmds.connectAttr(moduleNode+'.'+longName, joint+'Shape.addScaleY')
                cmds.connectAttr(moduleNode+'.'+longName, joint+'Shape.addScaleZ')
                #cmds.setAttr(moduleNode+'.'+longName, 0.2)
                cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.'+longName, 'module_transform_'+longName])

            cmds.addAttr(moduleNode, attributeType='enum', longName='Node_Rotation_Order', enumName='---------------------------:', keyable=True)
            for joint in self.joints:
                longName = mfunc.stripMRTNamespace(joint)[1]+'_rotate_order'
                cmds.addAttr(moduleNode, attributeType='enum', longName=longName, enumName='xyz:yzx:zxy:xzy:yxz:zyx:', defaultValue=0, keyable=True)
                cmds.connectAttr(moduleNode+'.'+longName, joint+'.rotateOrder')
                cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.'+longName, 'module_transform_'+longName+'_switch'])

            if self.proxyGeoStatus:
                cmds.addAttr(moduleNode, attributeType='enum', longName='Proxy_Geometry', enumName='---------------------------:', keyable=True)
                cmds.addAttr(moduleNode, attributeType='enum', longName='proxy_geometry_draw', enumName='Opaque:Transparent:', defaultValue=1, keyable=True)
                cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.proxy_geometry_draw', 'module_transform_proxy_geometry_draw_toggle'])

        if self.moduleName == 'SplineNode':

            moduleNode = self.moduleNamespace + ':splineStartHandleTransform'

            cmds.addAttr(moduleNode, attributeType='enum', longName='Node_Representation', enumName='----------------------:', keyable=True)
            cmds.addAttr(moduleNode, attributeType='float', longName='Global_size', hasMinValue=True, minValue=0, defaultValue=1, keyable=True)
            cmds.addAttr(moduleNode, attributeType='float', longName='Axis_Rotate', defaultValue=0, keyable=True)
            cmds.addAttr(moduleNode, attributeType='enum', longName='Node_Orientation_Info', enumName='Off:On:', defaultValue=1, keyable=True)
            cmds.addAttr(moduleNode, attributeType='enum', longName='Node_Orientation_Type', enumName='World:Object:', defaultValue=1, keyable=True)
            cmds.addAttr(moduleNode, attributeType='float', longName='Node_Local_Orientation_Representation_Size', hasMinValue=True, minValue=0.01, defaultValue=1, keyable=True)
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.Global_size', 'module_globalRepr_Size'])
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.Axis_Rotate', 'module_Axis_Rotate'])
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.Node_Orientation_Info', 'root_transform_Node_Orientation'])
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.Node_Orientation_Type', 'root_transform_Node_Orientation_Type'])
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.Node_Local_Orientation_Representation_Size', 'root_transform_Node_Orientation_Representation_Size'])

            if self.proxyGeoStatus:
                cmds.addAttr(moduleNode, attributeType='enum', longName='Proxy_Geometry', enumName='---------------------------:', keyable=True)
                cmds.addAttr(moduleNode, attributeType='enum', longName='proxy_geometry_draw', enumName='Opaque:Transparent:', defaultValue=1, keyable=True)
                cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.proxy_geometry_draw', 'module_transform_proxy_geometry_draw_toggle'])

        if self.moduleName == 'HingeNode':

            moduleNode = '|' + self.moduleGrp + '|' + self.moduleTransform

            cmds.addAttr(moduleNode, attributeType='enum', longName='Hinge_Orientation_Representation_Toggle', enumName='Off:On:', defaultValue=1, keyable=True)
            cmds.connectAttr(moduleNode+'.Hinge_Orientation_Representation_Toggle', self.joints[1]+'_IKhingeAxisRepresenation.visibility')
            cmds.connectAttr(moduleNode+'.Hinge_Orientation_Representation_Toggle', self.moduleNamespace+':IKPreferredRotationRepresentation.visibility')
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.Hinge_Orientation_Representation_Toggle', mfunc.stripMRTNamespace(self.joints[1])[1]+'_Hinge_Orientation_Representation_Toggle'])
            if not self.showOrientation:
                cmds.setAttr(moduleNode+'.Hinge_Orientation_Representation_Toggle', 0)

            cmds.addAttr(moduleNode, attributeType='enum', longName='Module_Hierarchy_Representation_Toggle', enumName='Off:On:', defaultValue=1, keyable=True)
            for joint in self.joints[:-1]:
                cmds.connectAttr(moduleNode+'.Module_Hierarchy_Representation_Toggle', joint+'_hierarchy_representation.visibility')
                cmds.connectAttr(moduleNode+'.Module_Hierarchy_Representation_Toggle', joint+'_segmentCurve.visibility')
            cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.Module_Hierarchy_Representation_Toggle', 'Module_Hierarchy_Representation_Toggle'])
            if not self.showHierarchy:
                cmds.setAttr(moduleNode+'.Module_Hierarchy_Representation_Toggle', 0)

            cmds.addAttr(moduleNode, attributeType='enum', longName='Node_Handle_Size', enumName='---------------------------:', keyable=True)
            for joint in self.joints:
                longName = mfunc.stripMRTNamespace(joint)[1]+'_handle_size'
                cmds.addAttr(moduleNode, attributeType='float', longName=longName, hasMinValue=True, minValue=0, defaultValue=1, keyable=True)
                cmds.connectAttr(moduleNode+'.'+longName, joint+'_controlShape_scaleClusterHandle.scaleX')
                cmds.connectAttr(moduleNode+'.'+longName, joint+'_controlShape_scaleClusterHandle.scaleY')
                cmds.connectAttr(moduleNode+'.'+longName, joint+'_controlShape_scaleClusterHandle.scaleZ')
                cmds.connectAttr(moduleNode+'.'+longName, joint+'_controlXShape.addScaleX')
                cmds.connectAttr(moduleNode+'.'+longName, joint+'_controlXShape.addScaleY')
                cmds.connectAttr(moduleNode+'.'+longName, joint+'_controlXShape.addScaleZ')
                #cmds.setAttr(moduleNode+'.'+longName, 0.2)
                cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.'+longName, 'module_transform_'+longName])

            cmds.addAttr(moduleNode, attributeType='enum', longName='Node_Rotation_Order', enumName='---------------------------:', keyable=True)
            for joint in self.joints:
                longName = mfunc.stripMRTNamespace(joint)[1]+'_rotate_order'
                cmds.addAttr(moduleNode, attributeType='enum', longName=longName, enumName='xyz:yzx:zxy:xzy:yxz:zyx:', defaultValue=0, keyable=True)
                cmds.connectAttr(moduleNode+'.'+longName, joint+'.rotateOrder')
                cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.'+longName, 'module_transform_'+longName+'_switch'])

            if self.proxyGeoStatus:
                cmds.addAttr(moduleNode, attributeType='enum', longName='Proxy_Geometry', enumName='---------------------------:', keyable=True)
                cmds.addAttr(moduleNode, attributeType='enum', longName='proxy_geometry_draw', enumName='Opaque:Transparent:', defaultValue=1, keyable=True)
                cmds.container(self.moduleContainer, edit=True, publishAndBind=[moduleNode+'.proxy_geometry_draw', 'module_transform_proxy_geometry_draw_toggle'])

    def createProxyGeo_elbows(self, geoType='sphere'):
        if geoType == 'sphere':
            filePathSuffix = 'MRT/elbow_proxySphereGeo.ma'
        if geoType == 'cube':
            filePathSuffix = 'MRT/elbow_proxyCubeGeo.ma'
        filePath = cmds.internalVar(userScriptDir=True) + filePathSuffix
        if self.mirrorModule:
            originalNamespace = cmds.getAttr(self.moduleGrp+'.mirrorModuleNamespace')
        index = 0
        hingeAimConstraints = []
        for joint in self.joints:
            cmds.file(filePath, i=True, prompt=False, ignoreVersion=True)
            proxyElbowGeoPreTransform = '_proxy_elbow_geo_preTransform'
            proxyElbowGeoScaleTransform = '_proxy_elbow_geo_scaleTransform'
            proxyElbowTransform = '_proxy_elbow_geo'
            if self.mirrorModule and self.proxyGeoMirrorInstance == 'On':
                originalNamespace = cmds.getAttr(self.moduleGrp+'.mirrorModuleNamespace')
                originalProxyElbowTransform = originalNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+proxyElbowTransform
                cmds.delete(proxyElbowTransform)
                transformInstance = cmds.duplicate(originalProxyElbowTransform, instanceLeaf=True, name='_proxy_elbow_geo')[0]
                cmds.parent(transformInstance, proxyElbowGeoScaleTransform, relative=True)
                if self.moduleName != 'HingeNode':
                    scaleFactorAxes = {'XY':[1, 1, -1], 'YZ':[-1, 1, 1], 'XZ':[1, -1, 1]}[self.onPlane]
                else:
                    scaleFactorAxes = {'XY':[-1, 1, 1], 'YZ':[1, 1, -1], 'XZ':[1, 1, -1]}[self.onPlane]
                cmds.setAttr(proxyElbowGeoScaleTransform+'.scale', *scaleFactorAxes)
            cmds.select(proxyElbowTransform+'.vtx[*]', replace=True)
            cmds.polyColorPerVertex(alpha=0.3, rgb=[0.663, 0.561, 0.319], notUndoable=True, colorDisplayOption=True)
            cmds.pointConstraint(joint, proxyElbowGeoPreTransform, maintainOffset=False, name=joint+'_pointConstraint')
            cmds.scaleConstraint(joint, proxyElbowGeoPreTransform, maintainOffset=False, name=joint+'_scaleConstraint')
            if self.moduleName == 'JointNode':
                aimVector = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[0]]
                upVector = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[1]]
                if self.numNodes > 1:
                    if index == 0:
                        cmds.aimConstraint(self.joints[index+1], proxyElbowGeoPreTransform, maintainOffset=True, aimVector=aimVector, upVector=upVector, worldUpVector=upVector, worldUpType='objectRotation', worldUpObject=joint, name=joint+'_'+proxyElbowGeoPreTransform+'_aimConstraint')
                    else:
                        cmds.aimConstraint(self.joints[index-1], proxyElbowGeoPreTransform, maintainOffset=True, aimVector=aimVector, upVector=upVector, worldUpVector=upVector, worldUpType='objectRotation', worldUpObject=joint, name=joint+'_'+proxyElbowGeoPreTransform+'_aimConstraint')
                if self.numNodes == 1:
                    cmds.orientConstraint(self.moduleNamespace+':single_orientation_representation_transform', proxyElbowGeoPreTransform, maintainOffset=True, name=proxyElbowGeoPreTransform+'_orientConstraint')
            if self.moduleName == 'HingeNode':
                aimVector = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[0]]
                upVector = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[1]]
                if index == 0:
                    aimConstraint = cmds.aimConstraint(self.joints[index+1], proxyElbowGeoPreTransform, maintainOffset=True, aimVector=aimVector, upVector=upVector, worldUpVector=upVector, worldUpType='objectRotation', worldUpObject=joint, name=joint+'_'+proxyElbowGeoPreTransform+'_aimConstraint')[0]
                else:
                    aimConstraint = cmds.aimConstraint(self.joints[index-1], proxyElbowGeoPreTransform, maintainOffset=True, aimVector=aimVector, upVector=upVector, worldUpVector=upVector, worldUpType='objectRotation', worldUpObject=joint, name=joint+'_'+proxyElbowGeoPreTransform+'_aimConstraint')[0]
                hingeAimConstraints.append(aimConstraint)

            if self.moduleName == 'SplineNode':
                cmds.orientConstraint(joint, proxyElbowGeoPreTransform, maintainOffset=True, name=joint+'_'+proxyElbowGeoPreTransform+'_orientConstraint')
            cmds.parent(proxyElbowGeoPreTransform, self.proxyGeoGrp, absolute=True)
            cmds.rename(proxyElbowGeoPreTransform, joint+proxyElbowGeoPreTransform)
            cmds.rename(proxyElbowGeoScaleTransform, joint+proxyElbowGeoScaleTransform)
            cmds.rename(proxyElbowTransform, joint+proxyElbowTransform)
            extra_nodes = [u'elbow_proxyGeo_uiConfigurationScriptNode', u'elbow_proxyGeo_sceneConfigurationScriptNode']
            for node in extra_nodes:
                if cmds.objExists(node):
                    cmds.delete(node)
            index += 1

        # Find and change the aim constraint offset values on hinge node in order to properly orient the elbow proxy geo.
        if hingeAimConstraints:
            l_val = [0.0, 90.0, 180.0, 270.0, 360.0]
            for constraint in hingeAimConstraints:
                for attr in ['X', 'Y', 'Z']:
                    val = cmds.getAttr(constraint+'.offset'+attr)
                    if not round(abs(val),0) in l_val:
                        l_cmp = {}
                        for item in l_val:
                            l_cmp[abs(item - abs(val))] = item
                        off_value = l_cmp[min(l_cmp)]
                        off_value = math.copysign(off_value, val)
                        cmds.setAttr(constraint+'.offset'+attr, off_value)

        cmds.select(clear=True)

    def createProxyGeo_bones(self):
        filePath = cmds.internalVar(userScriptDir=True) + 'MRT/bone_proxyGeo.ma'
        index = 0
        for joint in self.joints[:-1]:
            cmds.namespace(setNamespace=':')
            cmds.file(filePath, i=True, prompt=False, ignoreVersion=True)
            proxyBoneGeoPreTransform = 'proxy_bone_geo_preTransform'
            proxyBoneGeoScaleTransform = 'proxy_bone_geo_scaleTransform'
            proxyBoneTransform = 'proxy_bone_geo'

            if self.nodeAxes[0] == 'X':
                cmds.move(0,[proxyBoneGeoPreTransform+'.scalePivot', proxyBoneGeoPreTransform+'.rotatePivot'], moveX=True)
                cmds.move(0,[proxyBoneGeoScaleTransform+'.scalePivot', proxyBoneGeoScaleTransform+'.rotatePivot'], moveX=True)
                cmds.move(0,[proxyBoneTransform+'.scalePivot', proxyBoneTransform+'.rotatePivot'], moveX=True)
            if self.nodeAxes[0] == 'Y':
                cmds.move(0,[proxyBoneGeoPreTransform+'.scalePivot', proxyBoneGeoPreTransform+'.rotatePivot'], moveY=True)
                cmds.move(0,[proxyBoneGeoScaleTransform+'.scalePivot', proxyBoneGeoScaleTransform+'.rotatePivot'], moveY=True)
                cmds.move(0,[proxyBoneTransform+'.scalePivot', proxyBoneTransform+'.rotatePivot'], moveY=True)
            if self.nodeAxes[0] == 'Z':
                cmds.move(0,[proxyBoneGeoPreTransform+'.scalePivot', proxyBoneGeoPreTransform+'.rotatePivot'], moveZ=True)
                cmds.move(0,[proxyBoneGeoScaleTransform+'.scalePivot', proxyBoneGeoScaleTransform+'.rotatePivot'], moveZ=True)
                cmds.move(0,[proxyBoneTransform+'.scalePivot', proxyBoneTransform+'.rotatePivot'], moveZ=True)

            if self.mirrorModule and self.proxyGeoMirrorInstance == 'On':
                originalNamespace = cmds.getAttr(self.moduleGrp+'.mirrorModuleNamespace')
                originalProxyBoneTransform = originalNamespace+':'+mfunc.stripMRTNamespace(joint)[1]+'_'+proxyBoneTransform
                cmds.delete(proxyBoneTransform)
                transformInstance = cmds.duplicate(originalProxyBoneTransform, instanceLeaf=True, name='proxy_bone_geo')[0]
                cmds.parent(transformInstance, proxyBoneGeoScaleTransform, relative=True)
                if self.moduleName == 'HingeNode' and self.mirrorRotationFunc == 'Orientation':
                    scaleFactorAxes = {'X':[-1, 1, 1], 'Y':[1, -1, 1], 'Z':[1, 1, -1]}[self.nodeAxes[2]]
                else:
                    scaleFactorAxes = {'X':[-1, 1, 1], 'Y':[1, -1, 1], 'Z':[1, 1, -1]}[self.nodeAxes[1]]
                cmds.setAttr(proxyBoneGeoScaleTransform+'.scale', *scaleFactorAxes)

            cmds.select(proxyBoneTransform+'.vtx[*]', replace=True)
            cmds.polyColorPerVertex(alpha=0.3, rgb=[0.663, 0.561, 0.319], notUndoable=True, colorDisplayOption=True)
            if not self.mirrorModule:
                for axis in self.nodeAxes[1:]:
                    cmds.setAttr(proxyBoneGeoPreTransform+'.scale'+axis, 0.17)
                cmds.makeIdentity(proxyBoneGeoPreTransform, scale=True, apply=True)
            if self.mirrorModule and self.proxyGeoMirrorInstance == 'Off':
                for axis in self.nodeAxes[1:]:
                    cmds.setAttr(proxyBoneGeoPreTransform+'.scale'+axis, 0.17)
                cmds.makeIdentity(proxyBoneGeoPreTransform, scale=True, apply=True)

            cmds.parent(proxyBoneGeoPreTransform, self.proxyGeoGrp, absolute=True)

            tempConstraint = cmds.orientConstraint(joint, proxyBoneGeoPreTransform, maintainOffset=False)
            cmds.delete(tempConstraint)

            for axis in self.nodeAxes[1:]:
                cmds.connectAttr(self.moduleTransform+'.globalScale', proxyBoneGeoPreTransform+'.scale'+axis)
            ##curveInfo = joint + '_handleControlSegmentCurve_curveInfo'
            curveInfo = joint + '_segmentCurve_curveInfo'
            cmds.connectAttr(curveInfo+'.arcLength', proxyBoneGeoPreTransform+'.scale'+self.nodeAxes[0])
            ##cmds.pointConstraint(joint+'_handleControlSegmentCurve_startLocator', proxyBoneGeoPreTransform, maintainOffset=False, name=self.moduleNamespace+':'+proxyBoneGeoPreTransform+'_basePointConstraint')
            cmds.pointConstraint(joint+'_segmentCurve_startLocator', proxyBoneGeoPreTransform, maintainOffset=False, name=self.moduleNamespace+':'+proxyBoneGeoPreTransform+'_basePointConstraint')
            aimVector = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[0]]
            upVector = {'X':[1.0, 0.0, 0.0], 'Y':[0.0, 1.0, 0.0], 'Z':[0.0, 0.0, 1.0]}[self.nodeAxes[1]]

            cmds.aimConstraint(self.joints[index+1], proxyBoneGeoPreTransform, maintainOffset=False, aimVector=aimVector, upVector=upVector, worldUpVector=upVector, worldUpType='objectRotation', worldUpObject=joint, name=self.joints[index+1]+'_'+proxyBoneGeoPreTransform+'_aimConstraint')
            cmds.rename(proxyBoneGeoPreTransform, joint+'_'+proxyBoneGeoPreTransform)
            cmds.rename(proxyBoneGeoScaleTransform, joint+'_'+proxyBoneGeoScaleTransform)
            cmds.rename(proxyBoneTransform, joint+'_'+proxyBoneTransform)
            extra_nodes = [u'bone_proxyGeo_uiConfigurationScriptNode', u'bone_proxyGeo_sceneConfigurationScriptNode']
            for node in extra_nodes:
                if cmds.objExists(node):
                    cmds.delete(node)
            index += 1
        cmds.select(clear=True)

    def connectCustomOrientationReprToBoneProxies(self):
        if self.moduleName == 'JointNode':
            rotAxis = cmds.getAttr(self.moduleGrp+'.nodeOrient')
            rotAxis = rotAxis[0]
            for joint in self.joints[:-1]:
                ori_repr_control = joint+'_orientation_representation_transform'
                boneProxy_s_transform = joint+'_proxy_bone_geo_scaleTransform'
                if cmds.objExists(boneProxy_s_transform):
                    cmds.connectAttr(ori_repr_control+'.rotate'+rotAxis, boneProxy_s_transform+'.rotate'+rotAxis)
        if self.moduleName == 'SplineNode':
            startHandle = self.joints[0].rpartition(':')[0] + ':splineStartHandleTransform'
            for joint in self.joints:
                elbowProxy_s_transform = joint+'_proxy_elbow_geo_scaleTransform'
                if cmds.objExists(elbowProxy_s_transform):
                    cmds.connectAttr(startHandle+'.Axis_Rotate', elbowProxy_s_transform+'.rotateY')
