/* FFTW2-compatible API implemented with FFTW3 (x64 build shim). */
#ifndef HAMDRM_FFTW2_COMPAT_H
#define HAMDRM_FFTW2_COMPAT_H

#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef double fftw_real;

typedef struct {
	fftw_real re, im;
} fftw_complex;

typedef enum {
	FFTW_FORWARD = -1,
	FFTW_BACKWARD = 1
} fftw_direction;

typedef enum {
	FFTW_REAL_TO_COMPLEX = 1111,
	FFTW_COMPLEX_TO_REAL = 1112
} rfftw_direction;

#define FFTW_ESTIMATE (1 << 6)

struct fftw2_plan_s;
typedef struct fftw2_plan_s *fftw_plan;
typedef struct fftw2_plan_s *rfftw_plan;

/* Unique linker names — macros map Dream/Matlib calls onto these. */
fftw_plan hamdrm_fftw_create_plan(int n, fftw_direction dir, int flags);
void hamdrm_fftw_one(fftw_plan plan, fftw_complex *in, fftw_complex *out);
void hamdrm_fftw_destroy_plan(fftw_plan plan);

rfftw_plan hamdrm_rfftw_create_plan(int n, rfftw_direction dir, int flags);
void hamdrm_rfftw_one(rfftw_plan plan, fftw_real *in, fftw_real *out);
void hamdrm_rfftw_destroy_plan(rfftw_plan plan);

#define fftw_create_plan hamdrm_fftw_create_plan
#define fftw_one hamdrm_fftw_one
#define fftw_destroy_plan hamdrm_fftw_destroy_plan
#define rfftw_create_plan hamdrm_rfftw_create_plan
#define rfftw_one hamdrm_rfftw_one
#define rfftw_destroy_plan hamdrm_rfftw_destroy_plan

#ifdef __cplusplus
}
#endif

#endif /* HAMDRM_FFTW2_COMPAT_H */
