"""
scenario.py

A simulation of the diagnosis of a double AVC+flu disease.

2026-03-25
gabrielle.porcher@lisn.fr
frederic.boulanger@centralesupelec.fr
"""
# Change the module path to find the code in the parent directory
import sys
from os.path import dirname, basename
sys.path.append(dirname(__file__)+"/..")

# Change the current directory so that the idefix parser find the model files
import os 
os.chdir(dirname(__file__))

from idefix_parser import IdefixParser

IdefixParser.load_model("grippe_avc_sc.ifx")
IdefixParser.run_simulation({
	"conflict": "Conflit",
	"Time": "Temps",
	"Mass": "Masse",
	"Evolution of": "Évolution de la",
	"mass": "masse",
	"and conflict": "et du conflit",
	"['meningite']": "Méningite",
	"['grippe']": "Grippe",
	"['avc']": "AVC",
	"['grippe_avc']": "Grippe et AVC",
	
})
