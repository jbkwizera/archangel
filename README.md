# Modular Robot

A heterogeneous multi-robot system for anti-poaching and wildlife conservation
monitoring: a mobile ground station that deploys cooperating aerial drones,
built with decentralized, fault-tolerant coordination as a core requirement —
drones survive loss of the station, and the station survives loss of any
individual drone.

The project is inspired by marsupial robotics (a mobile "carrier" platform
that deploys and recovers smaller robots) and swarm robotics coordination
philosophy (capability emerging from many simple, cooperating units rather
than one monolithic design).

This is a multi-year, self-directed learning project. Development proceeds
simulation-first, starting with a single drone and centralized coordination,
and moving toward decentralization, degraded-communications handling, and
eventually real hardware.

## Status

🚧 Phase one (environment setup and simulation foundations) — in progress.

## Setup

Full host and container setup instructions live in [`docs/host_setup.md`](docs/host_setup.md).

Quick summary of the stack:

- **Host:** Ubuntu 26.04
- **Development environment:** Docker container running Ubuntu 24.04
- **Simulation:** ROS 2 Jazzy, Gazebo Harmonic, PX4 SITL

Detailed build-and-run instructions for the development container will be
added as later stories land (see `docs/host_setup.md` for what exists so far).

## Roadmap

A high-level phase roadmap will be added here as phase one nears completion.
