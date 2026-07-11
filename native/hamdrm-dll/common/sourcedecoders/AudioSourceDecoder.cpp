/******************************************************************************\
 * Technische Universitaet Darmstadt, Institut fuer Nachrichtentechnik
 * Copyright (c) 2001
 *
 * Author(s):
 *	Volker Fischer
 *
 * Description:
 *	Audio source decoder
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
 * FOR A PARTICULAR PURPOSE. See the GNU General Public License for more 1111
 * details.
 *
 * You should have received a copy of the GNU General Public License along with
 * this program; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 *
\******************************************************************************/

#include "AudioSourceDecoder.h"




/*
* Encoder                                                                      *
\******************************************************************************/
void CAudioSourceEncoder::ProcessDataInternal(CParameter& TransmParam)
{
	int i;

	/* Here, the AAC encoder must be put in --------------------------------- */
	/* Here is the recorded data. Now, the DRM AAC encoder must be put in to
	   encode this material and generate the _BINARY output data */

	if (bIsDataService == TRUE)
	{
// TODO: make a separate modul for data encoding
		/* Write data packets in stream */
		CVector<_BINARY> vecbiData;
		const int iNumPack = iOutputBlockSize / iTotPacketSize;
		int iPos = 0;

		for (int j = 0; j < iNumPack; j++)
		{
			/* Get new packet */
			DataEncoder.GeneratePacket(vecbiData);

			/* Put it on stream */
			for (i = 0; i < iTotPacketSize; i++)
			{
				(*pvecOutputData)[iPos] = vecbiData[i];
				iPos++;
			}
		}
	}
}

void CAudioSourceEncoder::InitInternal(CParameter& TransmParam)
{
	if (TransmParam.iNumDataService == 1)
	{
		bIsDataService = TRUE;
		iTotPacketSize = DataEncoder.Init(TransmParam);
	}
	else
	{
		bIsDataService = FALSE;
	}
	/* Define input and output block size */
	iOutputBlockSize = TransmParam.iNumDecodedBitsMSC;
	iInputBlockSize = 38400;
}

CAudioSourceEncoder::CAudioSourceEncoder()
{
}

CAudioSourceEncoder::~CAudioSourceEncoder()
{
}

/******************************************************************************\
* Decoder                                                                      *
\******************************************************************************/
void CAudioSourceDecoder::ProcessDataInternal(CParameter& ReceiverParam)
{

	/* Check if something went wrong in the initialization routine */
	if (DoNotProcessData == TRUE)
	{
		return;
	}

	/* Text Message ***********************************************************/
	/* Total frame size depends on whether text message is used or not */
	{
		bAudioIsOK = FALSE;
		iOutputBlockSize = 0;
	}

	if (bAudioIsOK) PostWinMessage(MS_MSC_CRC, 0);
	else if (bAudioWasOK) PostWinMessage(MS_MSC_CRC, 1);
	else PostWinMessage(MS_MSC_CRC, 2);
	bAudioWasOK = bAudioIsOK;

}

void CAudioSourceDecoder::InitInternal(CParameter& ReceiverParam)
{
/*
	Since we use the exception mechanism in this init routine, the sequence of
	the individual initializations is very important!
	Requirement for text message is "stream is used" and "audio service".
	Requirement for AAC decoding are the requirements above plus "audio coding
	is AAC"
*/
	int iCurAudioStreamID;
	int iCurSelServ;

	try
	{
		/* Init error flags and output block size parameter. The output block
		   size is set in the processing routine. We must set it here in case
		   of an error in the initialization, this part in the processing
		   routine is not being called */
		IsLPCAudio = FALSE;
		IsSPEEXAudio = FALSE;
		IsCELPAudio = FALSE;
		DoNotProcessData = FALSE;
		iOutputBlockSize = 2*38400; //2*37800;

		/* Get number of total input bits for this module */
		iInputBlockSize = ReceiverParam.iNumAudioDecoderBits;

		/* Get current selected audio service */
		iCurSelServ = ReceiverParam.GetCurSelAudioService();

		/* Current audio stream ID */
		iCurAudioStreamID =
			ReceiverParam.Service[iCurSelServ].AudioParam.iStreamID;

		/* The requirement for this module is that the stream is used and the
		   service is an audio service. Check it here */
		if ((ReceiverParam.Service[iCurSelServ].
			eAudDataFlag != CParameter::SF_AUDIO) ||
			(iCurAudioStreamID == STREAM_ID_NOT_USED))
		{
			throw CInitErr(ET_ALL);
		}

		/* Init text message application ------------------------------------ */
		switch (ReceiverParam.Service[iCurSelServ].AudioParam.bTextflag)
		{
		case TRUE:
			/* Total frame size is input block size minus the bytes for the text
			   message */
			iTotalFrameSize = iInputBlockSize -
				SIZEOF__BYTE * NUM_BYTES_TEXT_MESS_IN_AUD_STR;
			break;

		case FALSE:
			/* All bytes are used for AAC data, no text message present */
			iTotalFrameSize = iInputBlockSize;
			break;
		}


		/* Init for decoding -------------------------------------------- */
		if (ReceiverParam.Service[iCurSelServ].AudioParam.
			eAudioCoding == CParameter::AC_LPC)
		{
			IsLPCAudio = TRUE;
		}
		if (ReceiverParam.Service[iCurSelServ].AudioParam.
			eAudioCoding == CParameter::AC_SPEEX)
		{
			IsSPEEXAudio = TRUE;
		}
		if (ReceiverParam.Service[iCurSelServ].AudioParam.
			eAudioCoding == CParameter::AC_CELP)
		{
			IsCELPAudio = TRUE;
		}


	}

	catch (CInitErr CurErr)
	{
		switch (CurErr.eErrType)
		{
		case ET_ALL:
			/* An init error occurred, do not process data in this module */
			DoNotProcessData = TRUE;
			break;

		case ET_AAC:
			/* AAC part should not be decdoded, set flag */
			IsCELPAudio = FALSE;
			IsSPEEXAudio = FALSE;
			IsLPCAudio = FALSE;
			break;

		default:
			DoNotProcessData = TRUE;
		}
	}
}

CAudioSourceDecoder::CAudioSourceDecoder()
{
}

CAudioSourceDecoder::~CAudioSourceDecoder()
{
}
