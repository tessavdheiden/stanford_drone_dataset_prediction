#!/bin/bash


# TABLE 2: safeGAN
python3 scripts/train.py --output_dir 'models_sdd/safeGAN_DP4' --dataset_name 'bookstore_3' --pooling_dim 4 --pool_static 0 --lamb 0.0 --checkpoint_name 'sdd' --d_type 'local'
python3 scripts/train.py --output_dir 'models_sdd/safeGAN_SP' --dataset_name 'bookstore_3' --pooling_dim 2 --pool_static 1 --lamb 0.0 --checkpoint_name 'sdd' --d_type 'local'
python3 scripts/train.py --output_dir 'models_sdd/safeGAN_DP4_SP' --dataset_name 'bookstore_3' --pooling_dim 4 --pool_static 1 --lamb 0.0 --checkpoint_name 'sdd' --d_type 'local'

# TABLE 2: socialGAN
python3 scripts/train.py --output_dir 'models_sdd/socialGAN' --dataset_name 'bookstore_3' --pooling_dim 2 --pool_static 0 --lamb 0.0 --checkpoint_name 'sdd' --d_type 'global'

# TABLE 2: socialLSTM
python3 scripts/train.py --output_dir 'models_sdd/socialLSTM' --dataset_name 'bookstore_3' --pooling_dim 2 --pool_static 0 --lamb 0.0 --checkpoint_name 'sdd' --d_type 'global' --pooling_type 'spool'
