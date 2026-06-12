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

IdefixParser.load_model("pneumo.ifx")
IdefixParser.run_simulation({
  "Evolution of": "Evolution of",
  "mass": "mass",
  "and conflict": "and conflict",
  "Mass": "Mass",
  "Time": "Time",
  "conflict": "Conflict",
  "['typical_pneumo']": "Typical Pneumonia",
  "['atypical_pneumo']": "Atypical Pneumonia",
  "['flu']": "Flu",
  "['covid']": "Covid",
  "['atypical_pneumo', 'covid', 'flu', 'typical_pneumo']": "Total Ignorance"
})
