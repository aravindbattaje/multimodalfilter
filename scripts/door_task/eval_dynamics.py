import argparse
import dataclasses

import fannypack
import numpy as np
import torch
import torchfilter

import crossmodal

Task = crossmodal.tasks.DoorTask

# Move cache in case we're running on NFS (eg Juno), open PDB on quit
fannypack.data.set_cache_path(crossmodal.__path__[0] + "/../.cache")
fannypack.utils.pdb_safety_net()

# Parse args
parser = argparse.ArgumentParser()
parser.add_argument("--experiment-name", type=str)
parser.add_argument("--checkpoint-label", type=str, default=None)
parser.add_argument("--save", action="store_true")
args = parser.parse_args()

# Create Buddy and read experiment metadata
buddy = fannypack.utils.Buddy(args.experiment_name)
model_type = buddy.metadata["model_type"]
dataset_args = buddy.metadata["dataset_args"]

# Load model using experiment metadata
filter_model: torchfilter.base.Filter = Task.model_types[model_type]()
buddy.attach_model(filter_model)
buddy.load_checkpoint(label=args.checkpoint_label)

# Run eval
eval_helpers = crossmodal.eval_helpers
eval_helpers.configure(buddy=buddy, task=Task, dataset_args=dataset_args)
eval_results = eval_helpers.run_eval(eval_dynamics=True)

buddy.add_metadata({"dynamics_eval": eval_results})
