import torch
import torch.nn as nn
import torchfilter
import torchfilter.types as types
from fannypack.nn import resblocks

from . import layers


class PushDynamicsModel(torchfilter.base.DynamicsModel):
    def __init__(self, units=64):
        """Initializes a dynamics model for our door task."""

        super().__init__(state_dim=2)

        # Fixed dynamics covariance
        self.Q_scale_tril = nn.Parameter(
            torch.cholesky(torch.diag(torch.FloatTensor([0.02, 0.02]))),
            requires_grad=False,
        )

        # Build neural network
        self.state_layers = layers.state_layers(units=units)
        self.control_layers = layers.control_layers(units=units)
        self.shared_layers = nn.Sequential(
            nn.Linear(units * 2, units),
            resblocks.Linear(units),
            resblocks.Linear(units),
            resblocks.Linear(units),
            nn.Linear(units, self.state_dim + 1),
        )
        self.units = units

    def forward(
        self,
        *,
        initial_states: types.StatesTorch,
        controls: types.ControlsTorch,
    ) -> types.StatesTorch:
        N, state_dim = initial_states.shape[:2]
        assert state_dim == self.state_dim

        # (N, control_dim) => (N, units // 2)
        control_features = self.control_layers(controls)

        # (N, state_dim) => (N, units // 2)
        state_features = self.state_layers(initial_states)

        # (N, units)
        merged_features = torch.cat((control_features, state_features), dim=-1)

        # (N, units * 2) => (N, state_dim + 1)
        output_features = self.shared_layers(merged_features)

        # We separately compute a direction for our network and a scalar "gate"
        # These are multiplied to produce our final state output
        state_update_direction = output_features[..., :state_dim]
        state_update_gate = torch.sigmoid(output_features[..., -1:])
        state_update = state_update_direction * state_update_gate

        # Return residual-style state update, constant uncertainties
        states_new = initial_states + state_update
        scale_trils = self.Q_scale_tril[None, :, :].expand(N, state_dim, state_dim)
        return states_new, scale_trils


# RuntimeError: size mismatch, m1: [40 x 64], m2: [128 x 64] at /tmp/pip-req-build-58y_cjjl/aten/src/THC/generic/THCTensorMathBlas.cu:273
