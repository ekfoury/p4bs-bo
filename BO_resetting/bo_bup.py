import socket
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, RBF
from modAL.models import BayesianOptimizer
from modAL.acquisition import optimizer_EI, max_EI, max_PI, max_UCB, optimizer_PI, optimizer_UCB
import os 

class BO():
    def __init__(self, length_scale = 0.0325, kernel = RBF, alpha = 0.00000001, strategy = max_EI, MAXIMUM_VAL = 200000, GRID_UNIT_SIZE = 1000): #GRID_UNIT_SIZE = 1000
        self.length_scale = length_scale
        self.kernel = kernel
        self.alpha = alpha
        self.strategy = strategy
        self.regressor = GaussianProcessRegressor(kernel=kernel(length_scale), alpha = alpha)
        self.optimizer = BayesianOptimizer(estimator=self.regressor,query_strategy=strategy)
        self.grid = np.array([])
        self.bounds = None
        self.MAXIMUM_VAL = MAXIMUM_VAL
        self.GRID_UNIT_SIZE = GRID_UNIT_SIZE
        
    def reset(self):
        length_scale = self.length_scale
        kernel = self.kernel
        alpha = self.alpha
        strategy = self.strategy
        del self.regressor
        del self.optimizer
        self.__init__(length_scale, kernel, alpha, strategy)
    
    def suggest(self, tradeoff = 0.001):
        assert(len(self.grid) > 0)
        if(self.strategy == max_EI):
            optimizer_type = optimizer_EI
        elif(self.strategy == max_UCB):
            optimizer_type = optimizer_UCB
        acq = optimizer_type(self.optimizer, self.grid.reshape(-1,1), tradeoff=tradeoff)
        self.optimizer.query_idx, query_inst = self.optimizer.query(self.grid.reshape(-1, 1))
        print('optimizer.query_idx', self.optimizer.query_idx)
        print('optimizer.query_inst', query_inst)
        
        query_idx = [np.argmax(acq)]
        query_inst = np.asarray(self.grid[query_idx[0]]).reshape(1,-1)
        
        print('query_idx', query_idx)
        print('query_inst', query_inst)

        return acq, query_inst
    
    
    def update_bounds(self, minimum, maximum):        
        if(minimum != maximum and maximum - minimum >= self.GRID_UNIT_SIZE):
            self.bounds = [minimum, maximum]
            self.grid   = np.arange(self.scale_value(self.bounds[0]), self.scale_value(self.bounds[1]), self.scale_value(self.GRID_UNIT_SIZE))
        else:
            self.bounds = [minimum]
            self.grid = np.array(minimum)
        
    def scale_value(self, val):
        return val / self.MAXIMUM_VAL
        
    def rescale_value(self, val):
        return int(val * self.MAXIMUM_VAL)
   
    def teach(self, query_inst, target):
        self.optimizer.teach(np.asarray(query_inst), np.asarray([[target]]))
    
    def plot_regret(self, regrets):
        fig = plt.figure(figsize=(4, 4))
        fig.tight_layout()
        plt.xlabel('Iterations')
        plt.ylabel('Cumulative regret $R$')
        plt.grid(True)
        #plt.ylim(0, 20)
        plt.plot(regrets, '--b')
        fig.show()
        fig.savefig('regrets.pdf', bbox_inches="tight")
        
    def plot(self, acq, iteration = 0, propagation = 20000):

        y_pred, y_std = self.optimizer.predict(self.grid.reshape(-1,1), return_std=True)
        y_pred, y_std = y_pred.ravel(), y_std.ravel()
        X_max, y_max = self.optimizer.get_max()
        
        fig = plt.figure(figsize=(10, 1.0))
        fig.tight_layout()
        axes = fig.subplots(nrows=1, ncols=2)
        with plt.style.context('seaborn-white'):
            x_training = self.optimizer.X_training.flatten()
            x_training = [self.rescale_value(x)/ propagation for x in x_training]
            x_max = self.rescale_value(X_max) / propagation
            grid_ravel = [self.rescale_value(x)/ propagation for x in self.grid.ravel()]

            axes[1].scatter(x_training, -self.optimizer.y_training, c='k', s=20, label='Queried')
            axes[1].scatter(x_max, -y_max, s=40, c='r', label='Current optimum')
            #axes[0].set_ylim(-0.2, 1)
            axes[1].plot(grid_ravel, -y_pred, label='GP regressor')
            axes[1].fill_between(grid_ravel, -(y_pred - y_std), -(y_pred + y_std), alpha=0.5)
            axes[1].set_ylabel('$f(.)$')
            axes[1].set_xlabel('$x[BDP]$')
            axes[1].axvline(x=grid_ravel[np.argmax(acq)], ls='--', c='k', lw=1)
            
            axes[0].yaxis.set_major_formatter(ticker.FormatStrFormatter('%.2f'))
            axes[0].plot(grid_ravel, acq, c='r', linewidth=1.5, label='acq')
            axes[0].set_xlabel('$x[BDP]$')
            axes[0].set_ylabel('$u^{EI}$')
            axes[0].axvline(x=grid_ravel[np.argmax(acq)], ls='--', c='k', lw=1)
            fig.show()
            fig.savefig(str(iteration) + '_' + str(iteration)+'.pdf', bbox_inches="tight")    
    
'''  
bo = BO_Reset()
bo.update_bounds(2000, 200000)
acq, query_inst = bo.suggest()
bo.teach(query_inst, 0.5) 
acq, query_inst = bo.suggest()
bo.teach(query_inst, 0.3) 

bo.plot(acq)
'''