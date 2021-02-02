#!/usr/bin/env python3

# Copyright 2021 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import uuid
import time
import argparse

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rmf_task_msgs.srv import SubmitTask
from rmf_task_msgs.msg import TaskType, Delivery

###############################################################################


class TaskRequester:

    def __init__(self, argv=sys.argv):
        parser = argparse.ArgumentParser()
        parser.add_argument('-p', '--pickup', required=True,
                            type=str, help='Start waypoint')
        parser.add_argument('-pd', '--pickup_dispenser', required=True,
                            type=str, help='Pickup dispenser name')
        parser.add_argument('-d', '--dropoff', required=True,
                            type=str, help='Finish waypoint')
        parser.add_argument('-di', '--dropoff_ingestor', required=True,
                            type=str, help='Dropoff ingestor name')
        parser.add_argument('-st', '--start_time',
                            help='Start time from now in secs, default: 0',
                            type=int, default=0)
        parser.add_argument("--disable_sim_time", action="store_true",
                            help='Disable sim time, default: use sim time')

        self.args = parser.parse_args(argv[1:])
        self.node = rclpy.create_node('task_requester')
        self.submit_task_srv = self.node.create_client(
            SubmitTask, '/submit_task')

        # Will enable sim time as default
        if not self.args.disable_sim_time:
            param = Parameter("use_sim_time", Parameter.Type.BOOL, True)
            self.node.set_parameters([param])

    def generate_task_req_msg(self):
        req_msg = SubmitTask.Request()
        req_msg.description.task_type.type = TaskType.TYPE_DELIVERY

        delivery = Delivery()
        delivery.pickup_place_name = self.args.pickup
        delivery.pickup_dispenser = self.args.pickup_dispenser
        delivery.dropoff_place_name = self.args.dropoff
        delivery.dropoff_ingestor = self.args.dropoff_ingestor
        req_msg.description.delivery = delivery

        ros_start_time = self.node.get_clock().now().to_msg()
        ros_start_time.sec += self.args.start_time
        req_msg.description.start_time = ros_start_time
        return req_msg

    def main(self):
        if not self.submit_task_srv.wait_for_service(timeout_sec=3.0):
            self.node.get_logger().error('Dispatcher Node is not available')
            return

        req_msg = self.generate_task_req_msg()
        print(f"\nGenerated delivery request: \n {req_msg}\n")
        self.node.get_logger().info("Submitting Delivery Request")

        try:
            future = self.submit_task_srv.call_async(req_msg)
            rclpy.spin_until_future_complete(
                self.node, future, timeout_sec=1.0)
            response = future.result()
            if response is None:
                self.node.get_logger().error('/submit_task srv call failed')
            elif not response.task_id:
                self.node.get_logger().error(
                    'Dispatcher node failed to accept task')
            else:
                self.node.get_logger().info(
                    'Request was successfully submitted '
                    f'and assigned task_id: [{response.task_id}]')
        except Exception as e:
            self.node.get_logger().error('Error! Submit Srv failed %r' % (e,))


###############################################################################


def main(argv=sys.argv):
    rclpy.init(args=sys.argv)
    args_without_ros = rclpy.utilities.remove_ros_args(sys.argv)

    task_requester = TaskRequester(args_without_ros)
    task_requester.main()
    rclpy.shutdown()


if __name__ == '__main__':
    main(sys.argv)
