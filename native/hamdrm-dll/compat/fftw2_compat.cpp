/*
 * FFTW2 API shim over FFTW3.
 * Linker names are hamdrm_fftw_* (see fftw2_compat.h macros for Dream).
 */
#include <fftw3.h>
#include <stdlib.h>

enum { HAMDRM_FFTW_FORWARD = -1, HAMDRM_FFTW_BACKWARD = 1 };
enum { HAMDRM_FFTW_REAL_TO_COMPLEX = 1111, HAMDRM_FFTW_COMPLEX_TO_REAL = 1112 };

struct fftw2_plan_s {
	int n;
	int is_real;
	int forward;
	fftw_plan p3;
	fftw_complex *cbuf;
	fftw_complex *ctmp;
	double *rtmp;
};

struct hamdrm_cplx { double re, im; };

extern "C" {

struct fftw2_plan_s *hamdrm_fftw_create_plan(int n, int dir, int /*flags*/)
{
	fftw2_plan_s *p = new fftw2_plan_s();
	p->n = n;
	p->is_real = 0;
	p->forward = (dir == HAMDRM_FFTW_FORWARD) ? 1 : 0;
	p->cbuf = NULL;
	p->rtmp = NULL;
	p->ctmp = (fftw_complex *)fftw_malloc(sizeof(fftw_complex) * (size_t)n);
	p->p3 = fftw_plan_dft_1d(n, p->ctmp, p->ctmp, dir, FFTW_ESTIMATE);
	return p;
}

void hamdrm_fftw_one(struct fftw2_plan_s *plan, hamdrm_cplx *in, hamdrm_cplx *out)
{
	if (!plan || !plan->p3)
		return;
	fftw_execute_dft(plan->p3, (fftw_complex *)in, (fftw_complex *)out);
}

void hamdrm_fftw_destroy_plan(struct fftw2_plan_s *plan)
{
	if (!plan)
		return;
	if (plan->p3)
		fftw_destroy_plan(plan->p3);
	if (plan->cbuf)
		fftw_free(plan->cbuf);
	if (plan->ctmp)
		fftw_free(plan->ctmp);
	if (plan->rtmp)
		fftw_free(plan->rtmp);
	delete plan;
}

struct fftw2_plan_s *hamdrm_rfftw_create_plan(int n, int dir, int /*flags*/)
{
	fftw2_plan_s *p = new fftw2_plan_s();
	p->n = n;
	p->is_real = 1;
	p->forward = (dir == HAMDRM_FFTW_REAL_TO_COMPLEX) ? 1 : 0;
	p->ctmp = NULL;
	p->cbuf = (fftw_complex *)fftw_malloc(sizeof(fftw_complex) * (size_t)(n / 2 + 1));
	p->rtmp = (double *)fftw_malloc(sizeof(double) * (size_t)n);
	if (p->forward)
		p->p3 = fftw_plan_dft_r2c_1d(n, p->rtmp, p->cbuf, FFTW_ESTIMATE);
	else
		p->p3 = fftw_plan_dft_c2r_1d(n, p->cbuf, p->rtmp, FFTW_ESTIMATE);
	return p;
}

void hamdrm_rfftw_one(struct fftw2_plan_s *plan, double *in, double *out)
{
	if (!plan || !plan->p3 || !plan->cbuf)
		return;

	const int n = plan->n;

	if (plan->forward) {
		fftw_execute_dft_r2c(plan->p3, in, plan->cbuf);
		out[0] = plan->cbuf[0][0];
		for (int k = 1; k < n / 2; ++k) {
			out[k] = plan->cbuf[k][0];
			out[n - k] = plan->cbuf[k][1];
		}
		if ((n % 2) == 0)
			out[n / 2] = plan->cbuf[n / 2][0];
	} else {
		plan->cbuf[0][0] = in[0];
		plan->cbuf[0][1] = 0.0;
		for (int k = 1; k < n / 2; ++k) {
			plan->cbuf[k][0] = in[k];
			plan->cbuf[k][1] = in[n - k];
		}
		if ((n % 2) == 0) {
			plan->cbuf[n / 2][0] = in[n / 2];
			plan->cbuf[n / 2][1] = 0.0;
		}
		fftw_execute_dft_c2r(plan->p3, plan->cbuf, out);
	}
}

void hamdrm_rfftw_destroy_plan(struct fftw2_plan_s *plan)
{
	hamdrm_fftw_destroy_plan(plan);
}

} /* extern "C" */
