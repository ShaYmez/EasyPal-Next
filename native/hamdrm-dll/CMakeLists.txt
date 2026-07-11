cmake_minimum_required(VERSION 3.20)
project(hamdrm LANGUAGES CXX)

# 64-bit HamDRM DLL for EasyPal-Next (FFTW3 + FFTW2 API shim).
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
  message(FATAL_ERROR "hamdrm.dll must be built as 64-bit (x64).")
endif()

set(HAMDRM_ROOT "${CMAKE_CURRENT_SOURCE_DIR}")
set(FFTW64_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../deps/fftw64" CACHE PATH "FFTW3 x64 binaries")

if(NOT EXISTS "${FFTW64_DIR}/fftw3.h")
  message(FATAL_ERROR "FFTW3 headers not found at ${FFTW64_DIR}. Run scripts/fetch-fftw64.ps1 / download fftw-3.3.5-dll64.zip")
endif()

# Import library for libfftw3-3.dll (MSVC .lib or MinGW .dll.a)
if(MSVC)
  set(FFTW_IMPLIB "${FFTW64_DIR}/libfftw3-3.lib")
  if(NOT EXISTS "${FFTW_IMPLIB}")
    find_program(LIB_EXE lib REQUIRED)
    execute_process(
      COMMAND "${LIB_EXE}" /machine:x64 /def:libfftw3-3.def /out:libfftw3-3.lib
      WORKING_DIRECTORY "${FFTW64_DIR}"
      RESULT_VARIABLE _fftw_lib_rc
    )
    if(NOT _fftw_lib_rc EQUAL 0)
      message(FATAL_ERROR "Failed to generate libfftw3-3.lib from .def")
    endif()
  endif()
else()
  set(FFTW_IMPLIB "${FFTW64_DIR}/libfftw3-3.dll.a")
  if(NOT EXISTS "${FFTW_IMPLIB}")
    find_program(DLLTOOL_EXE dlltool REQUIRED)
    execute_process(
      COMMAND "${DLLTOOL_EXE}" -d libfftw3-3.def -l libfftw3-3.dll.a -D libfftw3-3.dll
      WORKING_DIRECTORY "${FFTW64_DIR}"
      RESULT_VARIABLE _fftw_lib_rc
    )
    if(NOT _fftw_lib_rc EQUAL 0)
      message(FATAL_ERROR "Failed to generate libfftw3-3.dll.a from .def")
    endif()
  endif()
endif()

set(HAMDRM_SOURCES
  hamdrm.cpp
  sound/Sound.cpp
  common/chanest/ChanEstTime.cpp
  common/chanest/ChannelEstimation.cpp
  common/chanest/TimeLinear.cpp
  common/chanest/TimeWiener.cpp
  common/datadecoding/DABMOT.cpp
  common/datadecoding/DataDecoder.cpp
  common/datadecoding/MOTSlideShow.cpp
  common/datadecoding/picpool.cpp
  common/libs/poolid.cpp
  common/FAC/FAC.cpp
  common/interleaver/BlockInterleaver.cpp
  common/interleaver/SymbolInterleaver.cpp
  common/matlib/MatlibSigProToolbox.cpp
  common/matlib/MatlibStdToolbox.cpp
  common/libs/callsign.cpp
  common/mlc/BitInterleaver.cpp
  common/mlc/ChannelCode.cpp
  common/mlc/ConvEncoder.cpp
  common/mlc/EnergyDispersal.cpp
  common/mlc/Metric.cpp
  common/mlc/MLC.cpp
  common/mlc/QAMMapping.cpp
  common/mlc/ViterbiDecoder.cpp
  common/ofdmcellmapping/CellMappingTable.cpp
  common/ofdmcellmapping/OFDMCellMapping.cpp
  common/resample/Resample.cpp
  common/sourcedecoders/AudioSourceDecoder.cpp
  common/sync/FreqSyncAcq.cpp
  common/sync/SyncUsingPil.cpp
  common/sync/TimeSync.cpp
  common/sync/TimeSyncTrack.cpp
  common/bsr.cpp
  common/CRC.cpp
  common/Data.cpp
  common/DrmReceiver.cpp
  common/DRMSignalIO.cpp
  common/DrmTransmitter.cpp
  common/fir.cpp
  common/InputResample.cpp
  common/MSCMultiplexer.cpp
  common/OFDM.cpp
  common/Parameter.cpp
  common/ptt.cpp
  compat/fftw2_compat.cpp
)

add_library(hamdrm SHARED ${HAMDRM_SOURCES} hamdrm.def)

target_include_directories(hamdrm PRIVATE
  "${HAMDRM_ROOT}"
  "${HAMDRM_ROOT}/common"
  "${HAMDRM_ROOT}/compat"
  "${FFTW64_DIR}"
)

target_compile_definitions(hamdrm PRIVATE
  WIN32
  _WINDOWS
  _USRDLL
  HAMDREAM_DLL_EXPORTS
  HAMDRM_USE_FFTW3_SHIM
  NDEBUG
  _CRT_SECURE_NO_WARNINGS
  _CRT_NONSTDC_NO_WARNINGS
)

if(MSVC)
  target_compile_options(hamdrm PRIVATE /W3 /EHsc /MP /bigobj)
  # Dream code is old; silence noisy but non-fatal warnings that drown real errors
  target_compile_options(hamdrm PRIVATE
    /wd4244 /wd4267 /wd4996 /wd4305 /wd4018 /wd4101 /wd4100 /wd4505
  )
endif()

target_link_libraries(hamdrm PRIVATE
  "${FFTW_IMPLIB}"
  winmm
  shell32
  user32
  kernel32
)

set_target_properties(hamdrm PROPERTIES
  OUTPUT_NAME "hamdrm"
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
  ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
  PREFIX ""
)

# Copy FFTW DLL next to hamdrm.dll
add_custom_command(TARGET hamdrm POST_BUILD
  COMMAND "${CMAKE_COMMAND}" -E copy_if_different
    "${FFTW64_DIR}/libfftw3-3.dll"
    "$<TARGET_FILE_DIR:hamdrm>/libfftw3-3.dll"
  COMMENT "Copy libfftw3-3.dll beside hamdrm.dll"
)
