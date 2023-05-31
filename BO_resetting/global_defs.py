# *****************************************************
# imports
# *****************************************************

import time
import math


# *****************************************************
# Global Variables/Constants
# *****************************************************
#### Juniper 
junos_hostname = 'INSERT_HERE'
junos_username = 'INSERT_HERE'
junos_password = 'INSERT_HERE'

#### Peak detection
lag_change = 50
thresh_change = 10
influence_change = 0.1 #0.1

### BO
STOPPING_BO =  1e-3 # 5

#### Others
avg_F = 0
THRESH_LOSS_EXPONENTIAL_INCREASE = 0.0025
MAXIMUM_BUFFER = 200000
MINIMUM_BUFFER = 10000
DEFAULT_BUFFER = 20000

# *****************************************************

