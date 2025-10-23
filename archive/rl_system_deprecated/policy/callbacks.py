from stable_baselines3.common.callbacks import BaseCallback
from utils.logger import log

class ProgressLoggingCallback(BaseCallback):
    """
    A custom callback that logs progress during training.
    """
    def __init__(self, verbose=0):
        super(ProgressLoggingCallback, self).__init__(verbose)
        self._last_log_step = 0

    def _on_step(self) -> bool:
        """
        This method will be called by the model after each call to `env.step()`.
        """
        # Log progress. For very short runs, log every step. For longer runs, log every 10.
        total_steps = self.training_env.get_attr("total_timesteps")[0]
        if total_steps > 0:
            progress = (self.num_timesteps / total_steps) * 100
            if total_steps <= 50 or self.num_timesteps % 10 == 0:
                log.info(f"Training progress: {self.num_timesteps}/{total_steps} steps ({progress:.1f}%)")
        return True
