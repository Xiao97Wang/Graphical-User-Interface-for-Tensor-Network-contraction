# Graphical-User-Interface-for-Tensor-Network-contraction

This code is made possible by ChatGPT o1 preview. 

It is the first graphical user interface that allows you to contract a tensor network by dragging the tensors by you hand. 


###############################################

use the following code to open the graphical User interface:

python GUI_TN_contraction_v002.py



(make sure your python can run numpy and PyQt5)

###############################################

Notes: 

Manually updating a local tensor:

After deleting/disconnecting local tensors, the leg information of some local tensors might fail to automatically update. 
Then, you can manually update the leg informations, by right-clicking the local tensor, clicking the "Set dimensions", and then do nothing but clicking "ok".


###############################################

Version updates:

v002: 
A disconnect botton is added. This allows you to disconnect a shared bond (i.e., edge) in the tensor network. 

