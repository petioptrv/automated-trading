from algotradepy.streamers.sim_streamer import SimulationDataStreamer

__all__ = ["SimulationDataStreamer"]

try:
    from algotradepy.streamers.polygon_streamer import PolygonDataStreamer

    __all__.append("PolygonDataStreamer")
except ImportError:
    pass
