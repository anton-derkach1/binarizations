// Authors: Sanjeeb Dash (extending the code of Angulo and Van Vyve)
// Copyright: IBM Corporation 2026

#include <fstream>
#include <iostream>
#include <vector>
#include <assert.h>
#include <math.h>
#include <limits.h>
#include <time.h>
//#include <ilcplex/cplex.h> SANJEEB: Removed this for local compilation
#include <cplex.h>
using namespace std;

#define XCONT 0
#define XINT 1

// Here VV stands for Angulo + Van-vyve, and BM for Bonami-Margot

#define PROBORIG 1  // fixed-charge problem in original spaec
#define PROBVVEXT 2 // VV fixed-charge problem in extended space + strengthening
#define PROBVVMIDEXT 3 // VV fixed-charge problem in extended space - strengthening
#define PROBBMEXT 4 // BM extended formulation - strengthening
                    // numbering is crucial here, assumption is options >= 4 are BM
#define PROBBMSTREXT 5 // BM extended formulation + strengthening
#define PROBNEWSTREXT 6 // hand-coded binarization, do not use without understanding what it does
#define PROBLOG 7 // logarithmic formulation
#define PROBLOGSTR 8 // basic logarithmic formulation + strengthening
#define PROBLOGEXTRA 9 // perfect log formulation
#define PROBLOGSTREXTRA 10 // perfect log formulation + strengthening



struct handle
{
  CPXENVptr envfct;
  CPXENVptr envzfct;

  CPXLPptr mipfct;
  CPXLPptr mipzfct;

  int datagen; // SANJEEB: 0 means read from file, else generate
  int readsums;
  int option; // one of PROBORIG ..
  int xtype;  // one of XCONT or XINT
  int n;
  int m;
  int modulo;

  vector<vector<int> > fcost;
  vector<vector<int> > vcost;

  vector<double> demand;
  vector<double> capacity;

  vector<vector<double> > aij;
  vector<vector<double> > aji;
  string filename; // SANJEEB: added to read data from file
};

int data(int n, int m, int modulo, double factor, int* it, int* seed, handle* handle)
{
  int sc = 0, sd = 0, scaled_sc = 0;
  int sc1 = 0, sd1 = 0;
  double theta = 0.0;
  ifstream infile;
	
  handle->envfct = NULL;
  handle->envzfct = NULL;

  handle->mipfct = NULL;
  handle->mipzfct = NULL;

  handle->n = n;
  handle->m = m;
  handle->modulo = modulo;

  handle->capacity.resize(n);
  handle->demand.resize(m);

  handle->aij.resize(n+1);
  handle->aji.resize(m+1);

  handle->fcost.resize(n);
  handle->vcost.resize(n);

  if (handle->datagen == 0){
    int m1, n1;
    infile.open(handle->filename, std::ios::in);
    infile >> m1;
    infile >> n1;
    if (m1 != m || n1 != n) std::cout << "Error in m, n in data file " + handle->filename;
	  
  }  
  for(int i = 0; i < n; i++)
    {
      if (handle->datagen)
	handle->capacity.at(i) = 1 + rand()%modulo;
      else
	infile >> handle->capacity.at(i);
      sc += handle->capacity.at(i);
    } 
  if (handle->datagen == 0 && handle->readsums == 1){
    infile >> sc1; 
    if (sc1 != sc) std::cout << "Error in capacity sum in data file " << sc << " " << sc1 << " " <<  handle->filename << endl;
  }
  
  for(int j = 0; j < m; j++)
    {
      if (handle->datagen)
	handle->demand.at(j) = 1 + rand()%modulo;
      else
	infile >> handle->demand.at(j);
      sd += handle->demand.at(j);
    }
  if (handle->datagen == 0 && handle->readsums == 1){
    infile >> sd1; 
    if (sd1 != sd) std::cout << "Error in capacity sum in data file " << sd << " " << sd1 << " " <<  handle->filename << endl;
  }

  scaled_sc = factor*sc;
  while(scaled_sc > sd)
    for(int j = 0; j < m && factor*sc > sd; j++)
      if(handle->demand.at(j) < modulo)
	{
	  handle->demand.at(j)++;
	  sd++;
	}

  while(scaled_sc < sd)
    for(int i = 0; i < n && factor*sc < sd; i++)
      if(handle->capacity.at(i) < modulo)
	{
	  handle->capacity.at(i)++;
	  sc++;
	  scaled_sc = factor * sc;
	}

  handle->demand.push_back(0);
  handle->capacity.push_back(0);

  cout << m << " " << n << endl;
  for(int i = 0; i < n; i++)
    cout << handle->capacity.at(i) << " ";
  cout << sc << endl;

  for(int j = 0; j < m; j++)
    cout << handle->demand.at(j) << " ";
  cout << sd << endl;

  for(int i = 0; i < n+1; i++)
    for(int j = 0; j < m+1; j++)
      {
	handle->aij.at(i).push_back(min(handle->capacity.at(i),handle->demand.at(j)));
	handle->aji.at(j).push_back(min(handle->capacity.at(i),handle->demand.at(j)));
      }

  double tcost;
  for(int i = 0; i < n; i++){
    for(int j = 0; j < m; j++)
      {
	if (handle->datagen)
	  handle->fcost.at(i).push_back(200 + rand()%600);
	else{
	  infile >> tcost; handle->fcost.at(i).push_back(tcost);
	}
	cout << handle->fcost.at(i).at(j) << " ";
	handle->vcost.at(i).push_back(floor((theta*handle->fcost.at(i).back()*(m+n-1))/((double)sc)));
      }
    cout << endl;
  }
  infile.close();
  return 0;
}

double newextcoef(int rhs, int var)
{
  double coef[7][6] =
    {{0, 0, 0, 0, 0, 0}, 
     {1, 0, 0, 0, 0, 0},
     {2, -1, 0, 0, 0, 0},
     {3, -2, 4, 0, 0, 0},
     {4, -3, 5, -2, 0, 0},
     {5, -4, 6, -3, 7, 0},
     {6, -5, 7, -4, 8, -3}};
    
  if (rhs <= 6){
    if (var > 6){
      cerr << "var cannot be greater than rhs in newextcoef\n";
      exit(-1);
    }
    return coef[rhs][var-1];
  }
  return (double)var;
}

void newextconstraint(vector<int> & rbeg, vector<int> & rind, vector<double> & rval, vector<double> &rhs, vector<char> & sense, vector<vector<vector<int> > > & z, int aij, handle *handle, int i, int j, int &nz)
{
  int nconstr[7] = {0, 0, 1, 3, 4, 5, 6}; 
  double coef2[1][2] = {{-1, 0}};
  double rhs2[1] = {0};

  double coef3[3][3] = {{0, -1, 1}, {-1, 1, -1}, {1, 0, 1}};
  double rhs3[3] = {0, 0, 1};


  double coef4[4][4] = {{0, 0, -1, 1}, {0, -1, 1, -1}, {-1, 1, -1, 1}, {1, 0, 1, 0}};
  double rhs4[4] = {0, 0, 0, 1};

  double coef5[5][5] = {{0, 0, 0, -1, 1}, {0, 0, -1, 1, -1}, {0, -1, 1, -1, 1}, {-1, 1, -1, 1, -1}, {1, 0, 1, 0, 1}};
  double rhs5[5] = {0, 0, 0, 0, 1};
  
  double coef6[6][6] = {{0, 0, 0, 0, -1, 1}, {0, 0, 0, -1, 1, -1}, {0, 0, -1, 1, -1, 1}, {0, -1, 1, -1, 1, -1}, {-1, 1, -1, 1, -1, 1},  {1, 0, 1, 0, 1, 0}};
  double rhs6[6] = {0, 0, 0, 0, 0, 1};

  if (aij <= 1) return;
  
  if (aij == 2){
    rbeg.push_back(nz);
    for (int l=0; l<2; l++){
      if (coef2[0][l] != 0){ rind.push_back(z.at(i).at(j).at(l+1)); rval.push_back(coef2[0][l]); nz++;}
    }
    sense.push_back('L');
    rhs.push_back(rhs2[0]);
  }
  if (aij == 3){
    for (int k=0; k < nconstr[aij]; k++){
      rbeg.push_back(nz);
      for (int l=0; l<aij; l++){
	if (coef3[k][l] != 0){ rind.push_back(z.at(i).at(j).at(l+1)); rval.push_back(coef3[k][l]); nz++;}
      }
      sense.push_back('L');
      rhs.push_back(rhs3[k]);
    }
  }    
  if (aij == 4){
    for (int k=0; k < nconstr[aij]; k++){
      rbeg.push_back(nz);
      for (int l=0; l<aij; l++){
	if (coef4[k][l] != 0){ rind.push_back(z.at(i).at(j).at(l+1)); rval.push_back(coef4[k][l]); nz++;}
      }
      sense.push_back('L');
      rhs.push_back(rhs4[k]);
    }
  }    
  if (aij == 5){
    for (int k=0; k < nconstr[aij]; k++){
      rbeg.push_back(nz);
      for (int l=0; l<aij; l++){
	if (coef5[k][l] != 0){ rind.push_back(z.at(i).at(j).at(l+1)); rval.push_back(coef5[k][l]); nz++;}
      }
      sense.push_back('L');
      rhs.push_back(rhs5[k]);
    }
  }    
  if (aij == 6){
    for (int k=0; k < nconstr[aij]; k++){
      rbeg.push_back(nz);
      for (int l=0; l<aij; l++){
	if (coef6[k][l] != 0){ rind.push_back(z.at(i).at(j).at(l+1)); rval.push_back(coef6[k][l]); nz++;}
      }
      sense.push_back('L');
      rhs.push_back(rhs6[k]);
    }
  }    
  if (aij >= 7){
    rbeg.push_back(nz);
    for (int l=0; l<aij; l++){
      rind.push_back(z.at(i).at(j).at(l+1)); rval.push_back(1.0); nz++;
    }
    sense.push_back('L');
    rhs.push_back(1.0);
  }
}

int createmip(handle* handle)
{
  int status, n = handle->n, m = handle->m, nz = 0, ncol = 0, nzsos = 0, nsos = 0;
  vector<vector<int> > x(n,vector<int>(m)), y(n,vector<int>(m)), lg(n, vector<int>(m));
  vector<vector<vector<vector<int> > > > f(n,vector<vector<vector<int> > > (m)), g(m,vector<vector<vector<int> > > (n));
  vector<vector<vector<int> > > z(n,vector<vector<int> > (m));
  vector<int> rbeg, rind, ind, sosind, sosbeg;
  vector<double> rval, rhs, obj, ub, soswt;
  vector<char> sense, ctype, sostype;
  vector<char*> cname;
  int orig_const = 0;
  int pw;
  
  for(int i = 0; i < n; i++)
    for(int j = 0; j < m; j++)
      {
	x.at(i).at(j) = ncol++;

	obj.push_back(handle->vcost.at(i).at(j));
	ub.push_back(handle->aij.at(i).at(j));
	if (handle->xtype == XINT) ctype.push_back('I');
	else ctype.push_back('C');
	ind.push_back(x.at(i).at(j));

	cname.resize(cname.size()+1);
	cname.back() = (char*)malloc(100*sizeof(char));
	sprintf(cname.back(),"x.%d.%d",i,j);
      }

  for(int i = 0; i < n; i++)
    for(int j = 0; j < m; j++)
      {
	y.at(i).at(j) = ncol++;

	obj.push_back(handle->fcost.at(i).at(j));
	ub.push_back(1);
	ctype.push_back('B');
	ind.push_back(y.at(i).at(j));

	cname.resize(cname.size()+1);
	cname.back() = (char*)malloc(100*sizeof(char));
	sprintf(cname.back(),"y.%d.%d",i,j);
      }

  if (handle->option == PROBORIG || orig_const)
    for(int i = 0; i < n; i++)
      {
	rbeg.push_back(nz);

	for(int j = 0; j < m; j++)
	  {
	    rind.push_back(x.at(i).at(j));
	    rval.push_back(1);
	    nz++;
	  }

	rhs.push_back(handle->capacity.at(i));
	sense.push_back('L');
      }

  if (handle->option == PROBORIG || orig_const) 
    for(int j = 0; j < m; j++)
      {
	rbeg.push_back(nz);

	for(int i = 0; i < n; i++)
	  {
	    rind.push_back(x.at(i).at(j));
	    rval.push_back(1);
	    nz++;
	  }

	rhs.push_back(handle->demand.at(j));
	sense.push_back('E');
      }
  // SANJEEB: constraints of the form x_ij - a_ij y_ij <= 0
  for(int i = 0; i < n; i++)
    for(int j = 0; j < m; j++)
      {
	rbeg.push_back(nz);

	rind.push_back(x.at(i).at(j));
	rval.push_back(1);
	nz++;

	rind.push_back(y.at(i).at(j));
	rval.push_back(-handle->aij.at(i).at(j));
	nz++;

	rhs.push_back(0);
	sense.push_back('L');
      }

  // SANJEEB: strenthening arising from the assumption that y_ij is positive (= 1) implies x_ij is at least 1.
  for(int i = 0; i < n; i++)
    for(int j = 0; j < m; j++)
      {
	rbeg.push_back(nz);

	rind.push_back(x.at(i).at(j));
	rval.push_back(-1);
	nz++;

	rind.push_back(y.at(i).at(j));
	rval.push_back(1);
	nz++;

	rhs.push_back(0);
	sense.push_back('L');
      }

  if (handle->option != PROBORIG) goto EXTPROB;
	
  handle->envfct = CPXopenCPLEX(&status);
  assert(!status);

  handle->mipfct = CPXcreateprob(handle->envfct, &status, "mipfct");
  assert(!status);

  status = CPXaddcols(handle->envfct, handle->mipfct, obj.size(), 0, &(obj.at(0)), NULL, NULL, NULL, NULL, &(ub.at(0)), &(cname.at(0)));
  assert(!status);

  status = CPXaddrows(handle->envfct, handle->mipfct, 0, rhs.size(),nz, &(rhs.at(0)), &(sense.at(0)), &(rbeg.at(0)), &(rind.at(0)), &(rval.at(0)), NULL, NULL);
  assert(!status);

  status = CPXchgctype(handle->envfct, handle->mipfct, ctype.size(), &(ind.at(0)), &(ctype.at(0)));
  assert(!status);

  if (handle->option == PROBORIG) goto CLEANUP;

 EXTPROB:

  
  for(int i = 0; i < n; i++)
    for(int j = 0; j < m; j++)
      {
	if (handle->option < PROBLOG)
	  lg[i][j] = handle->aij.at(i).at(j); 
	else{
	  int tlg = 0;
	  pw = 1;
	  while (pw <= handle->aij.at(i).at(j)){
	    tlg ++; pw *= 2;
	  }
	  lg[i][j] = tlg;
	}
	
	z.at(i).at(j).resize(lg[i][j]+1);
	sosbeg.push_back(nzsos);
	sostype.push_back('1');
	nsos++;

	for(int l = 0; l <= lg[i][j]; l++)
	  {
	    z.at(i).at(j).at(l) = ncol++;
	    sosind.push_back(z.at(i).at(j).at(l));
	    if (handle->option < PROBBMEXT)
	      soswt.push_back(l);
	    else
	      soswt.push_back(1.0);
	    nzsos++;

	    obj.push_back(0);
	    ub.push_back(1);
	    ctype.push_back('B');
	    ind.push_back(z.at(i).at(j).at(l));

	    cname.resize(cname.size()+1);
	    cname.back() = (char*)malloc(100*sizeof(char));
	    sprintf(cname.back(),"z.%d.%d.%d",i,j,l);
	  }
      }

  for(int i = 0; i < n; i++)
    for(int j = 0; j < m; j++)
      {
	rbeg.push_back(nz);

	rind.push_back(x.at(i).at(j));
	rval.push_back(-1);
	nz++;

	if (handle->option < PROBLOG){
	  for(int l = 1; l <= handle->aij.at(i).at(j); l++)
	    {
	      rind.push_back(z.at(i).at(j).at(l));
	      if (handle->option < PROBBMEXT)
		rval.push_back(l);
	      else if (handle->option < PROBNEWSTREXT)
		rval.push_back(1.0);
	      else 
		rval.push_back(newextcoef((int)(handle->aij.at(i).at(j)), l));
	      nz++;
	    }
	}
	else{
	  pw = 1;
	  
	  for(int l = 1; l <= lg[i][j]; l++)
	    {
	      rind.push_back(z.at(i).at(j).at(l));
	      rval.push_back(pw);
	      nz++;
	      pw *= 2;
	    }
	}
	
	rhs.push_back(0);
	sense.push_back('E');
      }

  if (!orig_const)
    for(int i = 0; i < n; i++)
      {
	rbeg.push_back(nz);

	for(int j = 0; j < m; j++){

	  if (handle->option < PROBLOG){
	    for(int l = 1; l <= handle->aij.at(i).at(j); l++)
	      {
		rind.push_back(z.at(i).at(j).at(l));
		if (handle->option < PROBBMEXT)
		  rval.push_back(l);
		else if (handle->option < PROBNEWSTREXT)
		  rval.push_back(1.0);
		else 
		  rval.push_back(newextcoef((int)(handle->aij.at(i).at(j)), l));
		nz++;
	      }
	  }
	  else{
	    pw = 1;
	    for(int l = 1; l <= lg[i][j]; l++)
	      {
		rind.push_back(z.at(i).at(j).at(l));
		rval.push_back(pw);
		nz++;
		pw *= 2;
	      }
	  }

	}
	rhs.push_back(handle->capacity.at(i));
	sense.push_back('L');
      }

  if (!orig_const)
    for(int j = 0; j < m; j++)
      {
	rbeg.push_back(nz);

	for(int i = 0; i < n; i++){
	  if (handle->option < PROBLOG){
	    for(int l = 1; l <= handle->aij.at(i).at(j); l++)
	      {
		rind.push_back(z.at(i).at(j).at(l));
		if (handle->option < PROBBMEXT)
		  rval.push_back(l);
		else if (handle->option < PROBNEWSTREXT)
		  rval.push_back(1.0);
		else 
		  rval.push_back(newextcoef((int)(handle->aij.at(i).at(j)), l));
		nz++;
	      }
	  }
	  else{
	    pw = 1;
	    for(int l = 1; l <= lg[i][j]; l++)
	      {
		rind.push_back(z.at(i).at(j).at(l));
		rval.push_back(pw);
		nz++;
		pw *= 2;
	      }
	  }
	}
	rhs.push_back(handle->demand.at(j));
	sense.push_back('E');
      }

  if (handle->option == PROBLOGSTR || handle->option == PROBLOGSTREXTRA || handle->option == PROBNEWSTREXT){
    for(int i = 0; i < n; i++)
      for(int j = 0; j < m; j++)
	{
	  rbeg.push_back(nz);

	  for(int l = 1; l <= lg[i][j]; l++)
	    {
	      rind.push_back(z.at(i).at(j).at(l));
	      rval.push_back(1.0);
	      nz++;
	    }

	  rind.push_back(y.at(i).at(j));
	  rval.push_back(-1);
	  nz++;
	  rhs.push_back(0);
	  sense.push_back('G');
	}
  }

  if (handle->option == PROBLOGEXTRA || handle->option == PROBLOGSTREXTRA){
    for(int i = 0; i < n; i++)
      for(int j = 0; j < m; j++)
	{
	  // find zeros in bit representation of integer, represent as bit 1, 2, etc.
	  vector<int> zeros(lg[i][j]+1, 0);
	  int sz = 0;
	  int hval = handle->aij.at(i).at(j);
	  
	  for(int l = 1, pw = 1; l <= lg[i][j]; l++){
	    if ((pw & hval) == 0)
	      zeros[l] = 1;
	    else
	      zeros[l] = 0;
	    pw *= 2;
	  }
	  for(int l = 1; l <= lg[i][j]; l++)
	    if (zeros[l] == 1){
	      rbeg.push_back(nz);
	      sz = 0;
	      
	      for (int k=l; k<=lg[i][j]; k++){
		if (k != l && zeros[k] == 1) continue;
		rind.push_back(z.at(i).at(j).at(k));
		rval.push_back(1.0);
		nz++;
		sz++;
	      }
	      rhs.push_back(sz-1);
	      sense.push_back('L');
	    }
	}
  }

  if (handle->option == PROBVVEXT || handle->option == PROBVVMIDEXT){
    for(int i = 0; i < n; i++)
      for(int j = 0; j < m; j++)
	{
	  rbeg.push_back(nz);

	  for(int l = 1; l <= handle->aij.at(i).at(j); l++)
	    {
	      rind.push_back(z.at(i).at(j).at(l));
	      rval.push_back(1);
	      nz++;
	    }

	  if (handle->option == PROBVVEXT){
	    rind.push_back(y.at(i).at(j));
	    rval.push_back(-1);
	    nz++;
	    rhs.push_back(0);
	    sense.push_back('E');
	  }
	  else{
	    rhs.push_back(1);
	    sense.push_back('L');
	  }
	}
  }
  else if (handle->option == PROBBMSTREXT){
    for(int i = 0; i < n; i++)
      for(int j = 0; j < m; j++){
	rbeg.push_back(nz);
	      
	rind.push_back(z.at(i).at(j).at(1));
	rval.push_back(1);
	nz++;

	rind.push_back(y.at(i).at(j));
	rval.push_back(-1);
	nz++;
	rhs.push_back(0);
	sense.push_back('E');
      }					
  }

  if (handle->option == PROBBMEXT || handle->option == PROBBMSTREXT){
    for(int i = 0; i < n; i++)
      for(int j = 0; j < m; j++)
	for(int l = 1; l <= handle->aij.at(i).at(j)-1; l++){
	  rbeg.push_back(nz);

	  rind.push_back(z.at(i).at(j).at(l));
	  rval.push_back(1);
	  nz++;

	  rind.push_back(z.at(i).at(j).at(l+1));
	  rval.push_back(-1);
	  nz++;

	  rhs.push_back(0);
	  sense.push_back('G');
	}
  }
  if (handle->option == PROBVVEXT)
    for(int i = 0; i < n; i++)
      for(int j = 0; j < m; j++)
	{
	  rbeg.push_back(nz);

	  rind.push_back(y.at(i).at(j));
	  rval.push_back(1);
	  nz++;

	  rind.push_back(z.at(i).at(j).at(0));
	  rval.push_back(1);
	  nz++;

	  rhs.push_back(1);
	  sense.push_back('E');
	}

  if (handle->option == PROBNEWSTREXT){
    for(int i = 0; i < n; i++)
      for(int j = 0; j < m; j++)
	{
	  newextconstraint (rbeg, rind, rval, rhs, sense, z, handle->aij.at(i).at(j), handle, i, j, nz);
	}
  }
  
  handle->envzfct = CPXopenCPLEX(&status);
  assert(!status);

  handle->mipzfct = CPXcreateprob(handle->envzfct, &status, "mipzfct");
  assert(!status);

  status = CPXaddcols(handle->envzfct, handle->mipzfct, obj.size(), 0, &(obj.at(0)), NULL, NULL, NULL, NULL, &(ub.at(0)), &(cname.at(0)));
  assert(!status);

  status = CPXaddrows(handle->envzfct, handle->mipzfct, 0, rhs.size(), nz, &(rhs.at(0)), &(sense.at(0)), &(rbeg.at(0)), &(rind.at(0)), &(rval.at(0)), NULL, NULL);
  assert(!status);

  status = CPXchgctype(handle->envzfct, handle->mipzfct, ctype.size(), &(ind.at(0)), &(ctype.at(0)));
  assert(!status);

 CLEANUP:
  for(vector<char*>::iterator s = cname.begin(); s != cname.end(); s++)
    free(*s);

  return 0;
}

void closeall(handle* handle)
{
  int status = 0;

  if(handle->mipfct)
    status = CPXfreeprob(handle->envfct, &(handle->mipfct));
  assert(!status);

  if(handle->mipzfct)
    status = CPXfreeprob(handle->envzfct, &(handle->mipzfct));
  assert(!status);

  if(handle->envfct)
    status = CPXcloseCPLEX(&(handle->envfct));
  assert(!status);

  if(handle->envzfct)
    status = CPXcloseCPLEX(&(handle->envzfct));
  assert(!status);

  free(handle);
}

int main(int argc, char *argv[]) {

  int status, n, m, modulo, r, seed=1, option=PROBORIG, xtype=XCONT;
  double factor;

  if (argc < 6){
    printf("usage: fctgen n m modulo factor r [seed>0] [probtype=1..5] [xtype=0/1]\n");
    printf("probtype = 1 - orig, 2 - orig ext, 3 - ext not strengthened, 4 - ext BM, 5 - ext BM strengthened\n");
    printf("probtype = 6 - specific hand-coded binarizaton for testing (do not use), 7 - basic log, 8 - log strengthened\n");
    printf("probtyp = 9 - prefect log, 10 - perfect log strengthened\n");
    return 0;
  }
  n = atoi(argv[1]);
  m = atoi(argv[2]);
  modulo = atoi(argv[3]);
  factor = atof(argv[4]);
  r = atoi(argv[5]);
  if (argc >= 7) seed = atoi(argv[6]);
  if (argc >= 8) option = atoi(argv[7]);
  if (argc >= 9) xtype = atoi(argv[8]);
	
  cout << "@ Size: " << n << " " << m << " " << modulo << " " << factor << " " << option << " " << xtype << endl;

  for(int it = 0; it < r; it++)
    {
      struct handle* handle = new(struct handle);
      char name[100], namez[100];
      handle->datagen = 1;
      handle->filename = "gg2";
      handle->readsums = 0;
      if(seed)
	{
	  cout << "srand: " << seed + it << endl;
	  srand(seed + it);
	}
      else
	srand(time(0));

      status = data(n, m, modulo, factor, &it, &seed, handle);
      if(status)
	continue;
      handle->option = option;
      handle->xtype = xtype;
		
      createmip(handle);

      if (option == PROBORIG){
	sprintf(name, "fct_%d_%d_%d_%03d_%d__%05d",n,m,modulo,(int)(factor*100), r, seed + it);
	cout << string(name) << endl;

	// SANJEEB: commented out the next two lines
	//status = CPXwriteprob(handle->envfct, handle->mipfct, string(name).append(".sav").c_str(), NULL);
	//assert(!status);

	status = CPXwriteprob(handle->envfct, handle->mipfct, string(name).append(".lp").c_str(), NULL);
	assert(!status);

	status = CPXfreeprob(handle->envfct, &(handle->mipfct));
	assert(!status);
      }
      else{
	sprintf(namez, "z%dfct_%d_%d_%d_%03d_%d__%05d",option, n,m,modulo,(int)(factor*100), r, seed + it);
	cout << string(namez) << endl;

	// SANJEEB: commented out the next two lines
	//status = CPXwriteprob(handle->envzfct, handle->mipzfct, string(namez).append(".sav").c_str(), NULL);
	//assert(!status);

	status = CPXwriteprob(handle->envzfct, handle->mipzfct, string(namez).append(".lp").c_str(), NULL);
	assert(!status);

	status = CPXfreeprob(handle->envzfct, &(handle->mipzfct));
	assert(!status);
      }
		
      cout << "@next" << endl;

      closeall(handle);
    }

  return 0;
}



