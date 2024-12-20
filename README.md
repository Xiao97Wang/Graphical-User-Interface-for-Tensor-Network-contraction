# Graphical-User-Interface-for-Tensor-Network-contraction

This code is made possible by ChatGPT o1 preview. 

It is the first graphical user interface that allows you to contract a tensor network by dragging the tensors by you hand. 


###############################################

What can this GUI do


realise tensor operations by draging and clicking
![image](https://github.com/user-attachments/assets/330d1b7c-6791-44b1-ba71-e5a86482ae37)



double-click a tensor to access its value
![image](https://github.com/user-attachments/assets/78ab59e0-c59a-4d93-963f-a5dd70a3f6ac)


###############################################

How to use:

Download the single .py file (the latest version is v003), then run the following to open the graphical User interface:

python GUI_TN_contraction_v003.py

(make sure your environment contains a python that can import numpy and PyQt5)

###############################################

Notes: 

Manually updating a local tensor:

After deleting/disconnecting local tensors, the leg information of some local tensors might fail to automatically update. 
Then, you can manually update the leg informations, by right-clicking the local tensor, clicking the "Set dimensions", and then do nothing but clicking "ok".


###############################################

Version updates:

v002: 
A disconnect botton is added. This allows you to disconnect a shared bond (i.e., edge) in the tensor network. 

v003:
The "fast contract" button is added, this will automatically perform contraction and insert the contracted tensor into the tensor network.
(The old contraction button is renamed as "detailed contraction".) 
The function "SVD Bond Compression" is added as a button, which allows to use SVD to compress the bond dimension between two connected local tensors.


