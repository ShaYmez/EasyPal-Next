/******************************************************************************\
 * Technische Universitaet Darmstadt, Institut fuer Nachrichtentechnik
 * Copyright (c) 2001
 *
 * Author(s):
 *	Volker Fischer
 *
 * Description:
 *	Transmit and receive data
 *
 ******************************************************************************
 *
 * This program is free software; you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation; either version 2 of the License, or (at your option) any later
 * version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
 * details.
 *
 * You should have received a copy of the GNU General Public License along with
 * this program; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 *
\******************************************************************************/

#include "DRMSignalIO.h"


/* Implementation *************************************************************/
/******************************************************************************\
* Transmitter                                                                  *
\******************************************************************************/
void CTransmitData::ProcessDataInternal(CParameter& Parameter)
{
	int i;

	/* Filtering of output signal (FIR filter) ------------------------------ */
	/* Transfer input data in Matlib library vector */
	for (i = 0; i < iInputBlockSize; i++)
	{
		rvecDataReal[i] = (*pvecInputData)[i].real();
	}

	/* Actual filter routine (use saved state vector) */
	rvecDataReal = Filter(rvecB, rvecA, rvecDataReal, rvecZReal);

	/* Convert vector type. Fill vector with symbols (collect them) */
	const int iNs = iInputBlockSize;
	for (i = 0; i < iInputBlockSize; i++)
	{
		const int iCurIndex = iBlockCnt * iInputBlockSize + i;

		/* Imaginary, real */
		const short sCurOutReal = (short) (rvecDataReal[i] * rNormFactor);

		/* Use real valued signal as output for both sound card channels */
		vecsDataOut[iCurIndex] = sCurOutReal;
	}

	iBlockCnt++;
	if (iBlockCnt == iNumBlocks)
	{
		iBlockCnt = 0;

		/* Write data to sound card. Must be a blocking function */
		pSound->Write(vecsDataOut);
	}

}

void CTransmitData::InitInternal(CParameter& TransmParam)
{
	/* Init vector for storing a complete DRM frame number of OFDM symbols */
	iBlockCnt = 0;
	iNumBlocks = TransmParam.iNumSymPerFrame;
	const int iTotalSize =
		TransmParam.iSymbolBlockSize * iNumBlocks; //@

	vecsDataOut.Init(iTotalSize);

	/* Init sound interface */
	pSound->InitPlayback(iTotalSize, TRUE);

	/* Init filter taps */
	rvecB.Init(NUM_TAPS_TRANSMFILTER);

	/* Choose correct filter for chosen DRM bandwidth. Also, adjust offset
	   frequency for different modes. E.g., 5 kHz mode is on the right side
	   of the DC frequency */
	float* pCurFilt;
	CReal rNormCurFreqOffset;

	switch (TransmParam.GetSpectrumOccup())
	{
	case SO_0:
		pCurFilt = fTransmFilt4_5;

		/* Completely on the right side of DC */
		rNormCurFreqOffset =
			(rDefCarOffset + (CReal) 2250.0) / SOUNDCRD_SAMPLE_RATE;
		break;

	case SO_1:
		pCurFilt = fTransmFilt5;

		/* Completely on the right side of DC */
		rNormCurFreqOffset =
			(rDefCarOffset + (CReal) 2500.0) / SOUNDCRD_SAMPLE_RATE; 
		break;
	}

	/* Modulate filter to shift it to the correct IF frequency */
	for (int i = 0; i < NUM_TAPS_TRANSMFILTER; i++)
		rvecB[i] = pCurFilt[i] * Cos((CReal) 2.0 * crPi * rNormCurFreqOffset * i);

	/* Only FIR filter */
	rvecA.Init(1);
	rvecA[0] = (CReal) 1.0;

	/* State memory (init with zeros) and data vector */
	rvecZReal.Init(NUM_TAPS_TRANSMFILTER - 1, (CReal) 0.0);
	rvecZImag.Init(NUM_TAPS_TRANSMFILTER - 1, (CReal) 0.0);
	rvecDataReal.Init(TransmParam.iSymbolBlockSize);
	rvecDataImag.Init(TransmParam.iSymbolBlockSize);

	/* All robustness modes and spectrum occupancies should have the same output
	   power. Calculate the normaization factor based on the average power of
	   symbol (the number 3000 was obtained through output tests) */
	// bei 3000 -> +- 6000
	// bei 9000 -> +- 20000 achtung, 12000 ist zuviel -> foldback
	// moeglich +-32000
	rNormFactor = (CReal) 6000.0 / Sqrt(TransmParam.rAvPowPerSymbol);

	/* Define block-size for input */
	iInputBlockSize = TransmParam.iSymbolBlockSize;
}

CTransmitData::~CTransmitData()
{
}

#define no_dc_tap 17*2

double the_dcsum = 0.0;
double dcsumbuf[no_dc_tap] = {0.0};
int dcsumbufpt = 0;
 
_REAL averdc = 0.0;

/******************************************************************************\
* Receive data from the sound card                                             *
\******************************************************************************/
void CReceiveData::ProcessDataInternal(CParameter& Parameter)
{
	int i;
	double dcsum = 0.0;

	{
		/* Using sound card ------------------------------------------------- */
		/* Get data from sound interface. The read function must be a
		   blocking function! */
		if (pSound->Read(vecsSoundBuffer) == FALSE)
			PostWinMessage(MS_IOINTERFACE, 0); /* green light */
		else
			PostWinMessage(MS_IOINTERFACE, 2); /* red light */

		/* Write data to output buffer */
		for (i = 0; i < iOutputBlockSize; i++)
		{
			/* Use only desired channel, chosen by "RECORDING_CHANNEL" */
			(*pvecOutputData)[i] =
				(_REAL) vecsSoundBuffer[i];
		}

		the_dcsum -= dcsumbuf[dcsumbufpt];
		dcsumbufpt++;
		if (dcsumbufpt >= no_dc_tap) dcsumbufpt = 0;
		dcsumbuf[dcsumbufpt] = dcsum / (double)iOutputBlockSize;  
		the_dcsum += dcsumbuf[dcsumbufpt];

		averdc = the_dcsum;
	}

	/* Copy data in buffer for spectrum calculation ------------------------- */
	vecrInpData.AddEnd((*pvecOutputData), iOutputBlockSize);


	/* Update level meter */
	SignalLevelMeter.Update((*pvecOutputData));
}

void CReceiveData::InitInternal(CParameter& Parameter)
{
	/* Init sound interface. Set it to one symbol. The sound card interface
	   has to taken care about the buffering data of a whole MSC block.
	   Use stereo input (* 2) */
	pSound->InitRecording(Parameter.iSymbolBlockSize ); //@ 

	/* Init buffer size for taking stereo input */
	vecsSoundBuffer.Init(Parameter.iSymbolBlockSize); //@ 

	/* Init signal meter */
	SignalLevelMeter.Init(0);

	/* Init Hanning Window */
	HanningWindow.Init();

	/* Define output block-size */
	iOutputBlockSize = Parameter.iSymbolBlockSize;
}

CReceiveData::~CReceiveData()
{
	/* Close file (if opened) */
	if (pFileReceiver != NULL)
		fclose(pFileReceiver);
}

void CHanningWindow::Init(void)
{

	const int iLenDSInputVector = 2048;
	vecrHannWind.Init(iLenDSInputVector);
	vecrHannWind = Hann(iLenDSInputVector);
	for (int i = 0; i < iLenDSInputVector; i++)
		vecrHannWind[i] *= 2.0;
	bIsInit = TRUE;
}

void CReceiveData::GetInputSpec(CVector<_REAL>& vecrData)
{
	int				i;
	CComplexVector	veccSpectrum;
	CRealVector		vecrFFTInput;
	_REAL			rNormSqMag;
	_REAL			rNormData;

	const int iLenInputVector = 2*2048;
	const int iLenDSInputVector = 2048;
	const int iLenSpec = 512;

	if (!HanningWindow.bIsInit) return;

	/* Init input and output vectors */
	vecrData.Init(iLenSpec, (_REAL) 0.0);

	/* Lock resources */
	Lock();

	rNormData = 0.2 * (_REAL)iLenInputVector * iLenInputVector * _MAXSHORT;

	veccSpectrum.Init(iLenSpec);

	/* Copy data from shift register in Matlib vector */
	vecrFFTInput.Init(iLenDSInputVector);
	for (i = 0; i < iLenDSInputVector; i++)
		vecrFFTInput[i] = vecrInpData[i*2] * HanningWindow.vecrHannWind[i];

	/* Get spectrum */
	veccSpectrum = rfft(vecrFFTInput);

	/* Log power spectrum data */
	for (i = 0; i < iLenSpec; i++)
	{
		rNormSqMag = SqMag(veccSpectrum[i]) / rNormData;
		vecrData[i] = sqrt(rNormSqMag);
	}

	/* Release resources */
	Unlock();
}

/* Level meter -------------------------------------------------------------- */
void CSignalLevelMeter::Update(_REAL rVal)
{
	/* Search for max */
	const _REAL rCurAbsVal = Abs(rVal);
	if (rCurAbsVal > rCurLevel)
		rCurLevel = rCurAbsVal;
}


void CSignalLevelMeter::Update(CVector<_REAL> vecrVal)
{
	/* Do the update for entire vector */
	const int iVecSize = vecrVal.Size();
	rCurLevel = 0;
	for (int i = 0; i < iVecSize; i+=2)
		Update(vecrVal[i]);
}

void CSignalLevelMeter::Update(CVector<_SAMPLE> vecsVal)
{
	/* Do the update for entire vector, convert to real */
	const int iVecSize = vecsVal.Size();
	rCurLevel = 0;
	for (int i = 0; i < iVecSize; i+=2)
		Update((_REAL) vecsVal[i]);
}

_REAL CSignalLevelMeter::Level()
{
	return rCurLevel / _MAXSHORT;
}
