import argparse

from gem5.components.boards.x86_board import X86Board
from gem5.components.memory import DualChannelDDR4_2400
from gem5.components.processors.simple_switchable_processor import SimpleSwitchableProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import PrivateL1PrivateL2CacheHierarchy
from gem5.isas import ISA
import os
from gem5.resources.resource import Resource
from gem5.resources.resource import CustomDiskImageResource
from gem5.simulate.simulator import Simulator
from gem5.simulate.exit_event import ExitEvent
from gem5.utils.requires import requires
import base64

parser = argparse.ArgumentParser(
    description="Run Rust multi-threaded benchmark in gem5 FS mode"
)
parser.add_argument(
    "--num_cpus",
    type=int,
    default=4,
    help="Number of simulated CPU cores (default: 4)",
)
parser.add_argument(
    "--threads",
    type=int,
    default=4,
    help="Number of threads for gem5_bench (default: 4)",
)
parser.add_argument(
    "--seed",
    type=int,
    default=1,
    help="Random seed for gem5_bench (default: 1)",
)
parser.add_argument(
    "--iters",
    type=int,
    default=1,
    help="Iterations for gem5_bench (default: 1)",
)
args = parser.parse_args()

requires(isa_required=ISA.X86)

# Setup processor with requested core count
processor = SimpleSwitchableProcessor(
    starting_core_type=CPUTypes.KVM,
    switch_core_type=CPUTypes.O3,
    num_cores=args.num_cpus,
)

board = X86Board(
    clk_freq="3GHz",
    processor=processor,
    memory=DualChannelDDR4_2400(size="3GB"),
    cache_hierarchy=PrivateL1PrivateL2CacheHierarchy(
        l1d_size="32kB", l1i_size="32kB", l2_size="256kB"
    ),
)


def on_exit():
    # 1st exit: boot finished -> switch KVM to O3
    print("Boot done, switching to O3")
    processor.switch()
    yield False  # continue simulation
    # 2nd exit: benchmark finished
    print("Benchmark done")
    yield True  # stop simulation


# Build the guest command with the dynamic arguments
cmd = "\n".join([
    "m5 exit",  # trigger boot end (switch to O3)
    "m5 resetstats",  # clear bootup statistics
    f"/home/gem5/gem5_bench --quiet --seed {args.seed} --iters {args.iters} --threads {args.threads}",
    "m5 dumpstats",  # dump benchmark statistics (Section 2)
    "m5 exit",  # trigger simulation completion
])

board.set_kernel_disk_workload(
    kernel=Resource("x86-linux-kernel-5.4.49"),
    disk_image=CustomDiskImageResource(
        local_path="/home/surya/stuff/gem5-ece565/x86-ubuntu-18.04-img",
        disk_root_partition="1",
    ),
    readfile_contents=cmd,
)

sim = Simulator(board=board, on_exit_event={ExitEvent.EXIT: on_exit()})
sim.run()


