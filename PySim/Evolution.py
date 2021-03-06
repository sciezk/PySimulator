'''
Created on Nov 6, 2011

@author: cryan

Functions for evolving the pulse sequence

'''

import numpy as np
from numpy import sin, cos

from scipy.constants import pi
from scipy.linalg import expm, eigh

from copy import deepcopy

#Try to load the CPPBackEnd
try:
    import PySim.CySim
    CPPBackEnd = True
except ImportError:
    CPPBackEnd = False
    
    
def expm_eigen(matIn, mult):
    '''
    Helper function to compute matrix exponential of Hermitian matrix
    '''
    dim = matIn.shape[0]
    D, V = eigh(matIn)
    return np.dot(V, np.exp(mult*D).repeat(dim).reshape((dim, dim))*V.conj().T), D, V

    
def evolution_unitary(pulseSequence, systemParams):
    '''
    Main function for evolving a state under unitary conditions
    '''
    
    #Some error checking
    assert pulseSequence.numControlLines==systemParams.numControlHams, 'Oops! We need the same number of control Hamiltonians as control lines.'
    
    if CPPBackEnd:
        return PySim.CySim.Cy_evolution(pulseSequence, systemParams, 'unitary')
    else:
    
        totU = np.eye(systemParams.dim)
        
        #Loop over each timestep in the sequence
        curTime = 0.0
        for timect, timeStep in enumerate(pulseSequence.timeSteps):
            tmpTime = 0.0 
            #Loop over the sub-pixels if we have a finer discretization
            while tmpTime < timeStep:
                #Choose the minimum of the time left or the sub pixel timestep
                subTimeStep = np.minimum(timeStep-tmpTime, pulseSequence.maxTimeStep)
    
                #Initialize the Hamiltonian to the drift Hamiltonian
                Htot = deepcopy(systemParams.Hnat)
                
                #Add each of the control Hamiltonians
                for controlct, tmpControl in enumerate(pulseSequence.controlLines):
                    tmpPhase = 2*pi*tmpControl.freq*curTime + tmpControl.phase
                    if tmpControl.controlType == 'rotating':
                        tmpMat = cos(tmpPhase)*systemParams.controlHams[controlct]['inphase'].matrix + sin(tmpPhase)*systemParams.controlHams[controlct]['quadrature'].matrix
                    elif tmpControl.controlType == 'sinusoidal':
                        tmpMat = cos(tmpPhase)*systemParams.controlHams[controlct]['inphase'].matrix
                    else:
                        raise TypeError('Unknown control type.')
                    tmpMat *= pulseSequence.controlAmps[controlct,timect]
                    Htot += tmpMat
    
                
                if pulseSequence.H_int is not None:
                    #Move the total Hamiltonian into the interaction frame
                    Htot.calc_interaction_frame(pulseSequence.H_int, curTime)
                    #Propagate the unitary
                    totU = np.dot(expm_eigen(Htot.interactionMatrix,-1j*2*pi*subTimeStep)[0],totU)
                else:
                    #Propagate the unitary
                    totU = np.dot(expm_eigen(Htot.matrix,-1j*2*pi*subTimeStep)[0],totU)
                
                #Update the times
                tmpTime += subTimeStep
                curTime += subTimeStep
                
        return totU

    
def evolution_lindblad(pulseSequence, systemParams, rhoIn):
    '''
    Main function for evolving a state with Lindladian dissipators conditions.
    
    Currently does not currently properly handle transformation of dissipators into interaction frame. 
    '''
    
    #Some error checking
    assert pulseSequence.numControlLines==systemParams.numControlHams, 'Oops! We need the same number of control Hamiltonians as control lines.'
    
    if CPPBackEnd:
        return PySim.CySim.Cy_evolution(pulseSequence, systemParams, 'lindblad')
    else:

    
        #Setup the super operators for the dissipators
        supDis = np.zeros((systemParams.dim**2, systemParams.dim**2), dtype=np.complex128)
        for tmpDis in systemParams.dissipators:
            supDis += tmpDis.superOpColStack()
            
        #Initialize the propagator
        totF = np.eye(systemParams.dim**2)
        
        #Loop over each timestep in the sequence
        curTime = 0.0
        for timect, timeStep in enumerate(pulseSequence.timeSteps):
            tmpTime = 0.0 
            #Loop over the sub-pixels if we have a finer discretization
            while tmpTime < timeStep:
                #Choose the minimum of the time left or the sub pixel timestep
                subTimeStep = np.minimum(timeStep-tmpTime, pulseSequence.maxTimeStep)
    
                #Initialize the Hamiltonian to the drift Hamiltonian
                Htot = deepcopy(systemParams.Hnat)
                
                #Add each of the control Hamiltonians
                for controlct, tmpControl in enumerate(pulseSequence.controlLines):
                    tmpPhase = 2*pi*tmpControl.freq*curTime + tmpControl.phase
                    if tmpControl.controlType == 'rotating':
                        tmpMat = cos(tmpPhase)*systemParams.controlHams[controlct]['inphase'].matrix + sin(tmpPhase)*systemParams.controlHams[controlct]['quadrature'].matrix
                    elif tmpControl.controlType == 'sinusoidal':
                        tmpMat = cos(tmpPhase)*systemParams.controlHams[controlct]['inphase'].matrix
                    else:
                        raise TypeError('Unknown control type.')
                    tmpMat *= pulseSequence.controlAmps[controlct,timect]
                    Htot += tmpMat
                   
                if pulseSequence.H_int is not None:
                    #Move the total Hamiltonian into the interaction frame
                    Htot.calc_interaction_frame(pulseSequence.H_int, curTime)
                    supHtot = Htot.superOpColStack(interactionMatrix=True)
                else:
                    supHtot = Htot.superOpColStack()
                
                
                #Propagate the unitary
                totF = np.dot(expm(subTimeStep*(1j*2*pi*supHtot + supDis)),totF)
                
                tmpTime += subTimeStep
                curTime += subTimeStep
                
        return totF

    
    
    
    

