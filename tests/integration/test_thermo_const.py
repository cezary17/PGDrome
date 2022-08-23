'''
    simple 1D PGD example (heat equation with a point heat source) with three PGD variables (space, time and heat input)
    solving PGD problem in standard way using FEM
    returning PGDModel (as forward model) or PGD instance
'''

import unittest
import dolfin
import fenics
import numpy as np

from pgdrome.solver import PGDProblem1
from pgdrome.model import PGDErrorComputation

def create_meshes(num_elem, ord, ranges):
    '''
    :param num_elem: list for each PG CO
    :param ord: list for each PG CO
    :param ranges: list for each PG CO
    :return: meshes and V
    '''

    print('create meshes')

    meshes = list()
    Vs = list()

    dim = len(num_elem)

    for i in range(dim):
        mesh_tmp = dolfin.IntervalMesh(num_elem[i], ranges[i][0], ranges[i][1])
        Vs_tmp = dolfin.FunctionSpace(mesh_tmp, 'CG', ord[i])

        meshes.append(mesh_tmp)
        Vs.append(Vs_tmp)

    return meshes, Vs

def create_bc(Vs,dom,param):
    # boundary conditions list

    # Initial condition
    def init(x, on_boundary):
        return x < 0.0 + 1E-5

    initCond = dolfin.DirichletBC(Vs[1], 0, init)

    return [0, initCond, 0]

def problem_assemble_lhs(fct_F,var_F,Fs,meshes,dom,param,typ,dim):
    # problem discription left hand side of DGL for each fixed point problem

    if typ == 'r':
        a = dolfin.Constant(dolfin.assemble(Fs[1].dx(0) * Fs[1] * dolfin.dx(meshes[1])) \
            * dolfin.assemble(Fs[2] * Fs[2] * dolfin.dx(meshes[2]))) \
            * param["rho"] * param["c_p"] * fct_F * var_F * dolfin.dx(meshes[0]) \
            + dolfin.Constant(dolfin.assemble(Fs[1] * Fs[1] * dolfin.dx(meshes[1])) \
            * dolfin.assemble(Fs[2] * Fs[2] * dolfin.dx(meshes[2]))) \
            * param["k"] * fct_F.dx(0) * var_F.dx(0) * dolfin.dx(meshes[0])
    if typ == 's':
        a = dolfin.Constant(dolfin.assemble(Fs[0] * Fs[0] * dolfin.dx(meshes[0])) \
            * dolfin.assemble(Fs[2] * Fs[2] * dolfin.dx(meshes[2]))) \
            * param["rho"] * param["c_p"] * fct_F.dx(0) * var_F * dolfin.dx(meshes[1]) \
            + dolfin.Constant(dolfin.assemble(Fs[0].dx(0) * Fs[0].dx(0) * dolfin.dx(meshes[0])) \
            * dolfin.assemble(Fs[2] * Fs[2] * dolfin.dx(meshes[2]))) \
            * param["k"] * fct_F * var_F * dolfin.dx(meshes[1])
    if typ == 'w':
        a = dolfin.Constant(dolfin.assemble(Fs[0] * Fs[0] * dolfin.dx(meshes[0])) \
            * dolfin.assemble(Fs[1].dx(0) * Fs[1] * dolfin.dx(meshes[1]))) \
            * param["rho"] * param["c_p"] * fct_F * var_F * dolfin.dx(meshes[2])\
            + dolfin.Constant(dolfin.assemble(Fs[0].dx(0) * Fs[0].dx(0) * dolfin.dx(meshes[0])) \
            * dolfin.assemble(Fs[1] * Fs[1] * dolfin.dx(meshes[1]))) \
            * param["k"] * fct_F * var_F * dolfin.dx(meshes[2])
    return a

def problem_assemble_rhs(fct_F,var_F,Fs,meshes,dom,param,Q,PGD_func,typ,nE,dim):
    # problem discription right hand side of DGL for each fixed point problem

    if typ == 'r':
        l = dolfin.Constant(dolfin.assemble(Q[1][0] * Fs[1] * dolfin.dx(meshes[1])) \
            * dolfin.assemble(Q[2][0] * Fs[2] * dolfin.dx(meshes[2]))) \
            * Q[0][0] * var_F * dolfin.dx(meshes[0]) 
        if nE > 0:
            for old in range(nE):
                l +=- dolfin.Constant(dolfin.assemble(PGD_func[1][old].dx(0) * Fs[1] * dolfin.dx(meshes[1])) \
                    * dolfin.assemble(PGD_func[2][old] * Fs[2] * dolfin.dx(meshes[2]))) \
                    * param["rho"] * param["c_p"] * PGD_func[0][old] * var_F * dolfin.dx(meshes[0]) \
                    - dolfin.Constant(dolfin.assemble(PGD_func[1][old] * Fs[1] * dolfin.dx(meshes[1])) \
                    * dolfin.assemble(PGD_func[2][old] * Fs[2] * dolfin.dx(meshes[2]))) \
                    * param["k"] * PGD_func[0][old].dx(0) * var_F.dx(0) * dolfin.dx(meshes[0])
    if typ == 's':
        l = dolfin.Constant(dolfin.assemble(Q[0][0] * Fs[0] * dolfin.dx(meshes[0])) \
            * dolfin.assemble(Q[2][0] * Fs[2] * dolfin.dx(meshes[2]))) \
            * Q[1][0] * var_F * dolfin.dx(meshes[1]) 
        if nE > 0:
            for old in range(nE):
                l +=- dolfin.Constant(dolfin.assemble(PGD_func[0][old] * Fs[0] * dolfin.dx(meshes[0])) \
                    * dolfin.assemble(PGD_func[2][old] * Fs[2] * dolfin.dx(meshes[2]))) \
                    * param["rho"] * param["c_p"] * PGD_func[1][old].dx(0) * var_F * dolfin.dx(meshes[1]) \
                    - dolfin.Constant(dolfin.assemble(PGD_func[0][old].dx(0) * Fs[0].dx(0) * dolfin.dx(meshes[0])) \
                    * dolfin.assemble(PGD_func[2][old] * Fs[2] * dolfin.dx(meshes[2]))) \
                    * param["k"] * PGD_func[1][old] * var_F * dolfin.dx(meshes[1])
    if typ == 'w':
        l = dolfin.Constant(dolfin.assemble(Q[0][0] * Fs[0] * dolfin.dx(meshes[0])) \
            * dolfin.assemble(Q[1][0] * Fs[1] * dolfin.dx(meshes[1]))) \
            * Q[2][0] * var_F * dolfin.dx(meshes[2]) 
        if nE > 0:
            for old in range(nE):
                l +=- dolfin.Constant(dolfin.assemble(PGD_func[0][old] * Fs[0] * dolfin.dx(meshes[0])) \
                    * dolfin.assemble(PGD_func[1][old].dx(0) * Fs[1] * dolfin.dx(meshes[1]))) \
                    * param["rho"] * param["c_p"] * PGD_func[2][old] * var_F * dolfin.dx(meshes[2]) \
                    - dolfin.Constant(dolfin.assemble(PGD_func[0][old].dx(0) * Fs[0].dx(0) * dolfin.dx(meshes[0])) \
                    * dolfin.assemble(PGD_func[1][old] * Fs[1] * dolfin.dx(meshes[1]))) \
                    * param["k"] * PGD_func[2][old] * var_F * dolfin.dx(meshes[2])
    return l

def main(vs, params, name=None):
    '''computation of PGD solution for given problem '''

    # define some parameters
    param = params

    # define heat source in x, t and eta
    q1 = [dolfin.Expression('x[0] < 0.05 - af + DOLFIN_EPS ? p1 : (x[0] > 0.05 + af - DOLFIN_EPS ? p1 : p2)', degree=4, af=0.02, p1=0, p2=param['p2'])]
    q2 = [dolfin.Expression('1.0', degree=1)]
    q3 = [dolfin.Expression('x[0]', degree=1)]

    prob = ['r', 's', 'w'] # problems according problem_assemble_fcts
    seq_fp = np.arange(len(vs))  # default sequence of Fixed Point iteration
    PGD_nmax = 15      # max number of PGD modes

    pgd_prob = PGDProblem1(name='1DHeatEqu-PGD-XTEta', name_coord=['X', 'T', 'Eta'],
                           modes_info=['T_x', 'Node', 'Scalar'],
                           Vs=vs, dom=0, bc_fct=create_bc, load=[q1,q2,q3],
                           param=param, rhs_fct=problem_assemble_rhs,
                           lhs_fct=problem_assemble_lhs, probs=prob, seq_fp=seq_fp,
                           PGD_nmax=PGD_nmax)

    # possible solver parameters (if not given then default values will be used!)
    pgd_prob.stop_fp = 'chady'
    # pgd_prob.stop_fp = 'norm'
    pgd_prob.max_fp_it = 50
    pgd_prob.tol_fp_it = 1e-5 #1e-3
    pgd_prob.fp_init = 'randomized'

    pgd_prob.solve_PGD(_problem='linear')
    # pgd_prob.solve_PGD(_problem='linear',solve_modes=["FEM","FEM","direct"]) # solve normal
    # pgd_prob.solve_PGD(_problem = 'nonlinear', settings = {"relative_tolerance": 1e-8, "linear_solver": "mumps"})
    print(pgd_prob.simulation_info)
    print('PGD Amplitude', pgd_prob.amplitude)
    input()

    pgd_s = pgd_prob.return_PGD()  # as PGD class instance
    
    return pgd_s, param

# TEST: PGD result VS FEM result
#==============================================================================  

# Finite Element Model
#=======================================
class Reference_solution():
    
    def __init__(self,Vs=[], param=[], meshes=[], x_fixed=[]):
        
        self.Vs = Vs # Location
        self.param = param # Parameters
        self.meshes = meshes # Meshes
        self.x_fixed = x_fixed
        
        # Dirichlet BC:
        self.bc = create_bc(self.Vs,0,self.param)
        
    def fem_definition(self,t_max, eta):        
        rho = self.param['rho']                                  # material density [kg/m³]
        k = self.param['k']                                     # heat conductivity [W/m°C]
        cp = self.param['c_p']                                  # specific heat capacity [J/kg°C]
        T_amb = 0
        time_points = np.linspace(0, t_max, num=len(self.meshes[1].coordinates()))
        dt = time_points[1]-time_points[0]
        # Define initial value
        T_n = fenics.project(fenics.Expression("T_amb", domain=self.meshes[0], degree=4, T_amb=T_amb), self.Vs[0])
        # Define goldak heat input         
        q = fenics.Expression('x[0] < 0.05 - af + DOLFIN_EPS ? p1 : (x[0] > 0.05 + af - DOLFIN_EPS ? p1 : p2)', degree=4, af=0.02, p1=0, p2=eta*self.param['p2'])
        # Define problem functions
        T = fenics.TrialFunction(self.Vs[0])
        v = fenics.TestFunction(self.Vs[0])

        # Collect variational form
        F =  rho*cp*T*v*fenics.dx \
            + dt*k*fenics.dot(fenics.grad(T), fenics.grad(v))*fenics.dx \
            - (dt*q + rho*cp*T_n)*v*fenics.dx
        a, L = fenics.lhs(F), fenics.rhs(F)
        
        # Time-stepping
        T = fenics.Function(self.Vs[0])
        for n in range(len(time_points)-1):
            # Compute solution
            fenics.solve(a == L, T)
            # Update previous solution
            T_n.assign(T)
            
        # If specific points are given
        if self.x_fixed:
            T_out = np.zeros((len(self.x_fixed),self.meshes[0].topology().dim()))
            for i in range(len(self.x_fixed)):
                T_out[i,:]=np.array(T(self.x_fixed[i]))
            return T_out
        else:
            return T # return full vector
        
        # return T
            
    def __call__(self, data_test):
        
        # sampled variable values
        t_max = data_test[0]    # last time point
        eta = data_test[1]      # arc efficiency
                
        ref_sol = self.fem_definition(t_max, eta)
        
        return ref_sol
 
# PGD model and Error computation
#=======================================
class PGDproblem(unittest.TestCase):
    
    def setUp(self):
        
        # global parameters
        self.ord = 1  # 1 # 2 # order for each mesh
        self.ords = [self.ord, self.ord, self.ord]
        self.ranges = [[0., 0.1],  # xmin, xmax
                  [0., 10.],  # tmin, tmax
                  [0.7, 0.9]]  # etamin, etamax

        # sampling parameters
        self.fixed_dim = [0] # Fixed variable
        self.n_samples = 10 # Number of samples

        self.param = {"rho": 7100, "c_p": 3100, "k": 100, "p2":10e9}
        # self.param = {"rho": 1, "c_p": 1, "k": 100/(7100*3100), 'p2':10e9/(7100*3100)}

    def TearDown(self):
        pass
    
    def test_solver(self):
        
        # MESH
        #======================================================================
        meshes, Vs = create_meshes([1000, 500, 50], self.ords, self.ranges)
        
        # Computing solution and error
        #======================================================================
        pgd_test, param = main(Vs, self.param) # Computing PGD

        fun_FOM = Reference_solution(Vs=Vs, param=self.param, meshes=meshes) # Computing Full-Order model: FEM
        
        error_uPGD = PGDErrorComputation(fixed_dim = self.fixed_dim,
                                          n_samples = self.n_samples,
                                          FOM_model = fun_FOM,
                                          PGD_model = pgd_test
                                          )
        
        errorL2, mean_errorL2, max_errorL2 = error_uPGD.evaluate_error() # Computing Error
        
        print('Mean error',mean_errorL2)
        print('Max. error',max_errorL2)
        
        # self.assertTrue(mean_errorL2<0.004)
        
        # Computing solution and error
        #======================================================================
        
        # Create variables array:
        x_test = [[0.05]]  # x (fixed variable)
        data_test = [[1., 0.8],[5.,0.8],[10.,0.8]] # t, eta
        
        # Solve Full-oorder model: FEM
        fun_FOM2 = Reference_solution(Vs=Vs, param=param, meshes=meshes, x_fixed=x_test) # Computing Full-Order model: FEM

        # Compute error:
        error_uPGD2 = PGDErrorComputation(fixed_dim = self.fixed_dim,
                                          FOM_model = fun_FOM2,
                                          PGD_model = pgd_test,
                                          data_test = data_test,
                                          fixed_var = x_test
                                          )

        error2, mean_error2, max_error2 = error_uPGD2.evaluate_error()  
        
        # Plot solution over space at specific time
        import matplotlib.pyplot as plt
        plt.figure()
        u_fem1 = fun_FOM(data_test[0])
        u_pgd1 = pgd_test.evaluate(0, [1, 2], [data_test[0][0], data_test[0][1]], 0)
        u_fem2 = fun_FOM(data_test[-1])
        u_pgd2 = pgd_test.evaluate(0, [1, 2], [data_test[-1][0], data_test[-1][1]], 0)
        plt.plot(pgd_test.mesh[0].dataX, u_pgd1.compute_vertex_values()[:], '-*b', label=f"PGD at {data_test[0]}s")
        plt.plot(pgd_test.mesh[0].dataX, u_fem1.compute_vertex_values()[:], '-or', label='FEM')
        plt.plot(pgd_test.mesh[0].dataX, u_pgd2.compute_vertex_values()[:], '-*g', label=f"PGD at {data_test[-1]}s")
        plt.plot(pgd_test.mesh[0].dataX, u_fem2.compute_vertex_values()[:], '-oy', label='FEM')
        plt.title(f"PGD solution at {data_test[0][0]}s over space")
        plt.xlabel("Space x [m]")
        plt.ylabel("Temperature T [°C]")
        plt.legend()
        plt.draw()
        plt.show()
        
        print('Mean error',mean_error2)
        print('Max. error',max_error2)
        
        self.assertTrue(mean_error2<0.0055)
        
if __name__ == '__main__':
    dolfin.set_log_level(dolfin.LogLevel.ERROR)

    import logging
    logging.basicConfig(level=logging.INFO)

    unittest.main()
