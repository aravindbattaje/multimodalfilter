import argparse

import fannypack
import torchfilter

import crossmodal

Task = crossmodal.tasks.PushTask

# Move cache in case we're running on NFS (eg Juno), open PDB on quit
fannypack.data.set_cache_path(crossmodal.__path__[0] + "/../.cache")
fannypack.utils.pdb_safety_net()

# Parse args
parser = argparse.ArgumentParser()
parser.add_argument("--experiment-name", type=str)
parser.add_argument("--checkpoint-label", type=str, default=None)
parser.add_argument("--save", action="store_true")
parser.add_argument("--measurement_init", action="store_true")

Task.add_dataset_arguments(parser)

args = parser.parse_args()
dataset_args = Task.get_dataset_args(args)

# Create Buddy and read experiment metadata
buddy = fannypack.utils.Buddy(args.experiment_name)
model_type = buddy.metadata["model_type"]
# dataset_args = buddy.metadata["dataset_args"]

# Load model using experiment metadata
filter_model: torchfilter.base.Filter = Task.model_types[model_type]()
buddy.attach_model(filter_model)
buddy.load_checkpoint(label=args.checkpoint_label)

# Run eval
eval_helpers = crossmodal.eval_helpers
eval_helpers.configure(buddy=buddy, task=Task, dataset_args=dataset_args)
eval_results = eval_helpers.run_eval_stats(measurement_initialize=args.measurement_init)

# Save eval results
if args.save:
    buddy.add_metadata({"eval_results": eval_results})
