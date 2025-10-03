import os

from ament_index_python.packages import get_package_share_directory


from launch import LaunchDescription, LaunchContext
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler, LogInfo, ExecuteProcess, EmitEvent, OpaqueFunction, SetEnvironmentVariable, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessStart, OnExecutionComplete, OnProcessExit
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, TextSubstitution, PythonExpression
from launch.conditions import IfCondition, UnlessCondition
from launch.events import Shutdown

from launch_ros.actions import Node
import xacro


package_name = 'ppp_bot'


def launch_localization(context: LaunchContext, world_name):
    world_name_str = context.perform_substitution(world_name)
    pkg_path = os.path.join(get_package_share_directory('ppp_bot'))
    map_path = os.path.join(pkg_path, 'maps', f'{world_name_str}.yaml')
    localization_launcher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_path, 'launch', 'localization.launch.py')
        ]),
        launch_arguments={
            'use_sim_time': 'true',
            'map': map_path
        }.items(),
        condition=IfCondition(LaunchConfiguration('localization'))
    )
    return [localization_launcher]


def generate_launch_description():
    # Launch Configuration
    world_name = LaunchConfiguration('world_name')
    use_rviz = LaunchConfiguration('use_rviz')
    use_teleop = LaunchConfiguration('use_teleop')
    use_joystick = LaunchConfiguration('use_joystick')
    localization = LaunchConfiguration('localization')
    x_pose = LaunchConfiguration('x_pose')
    y_pose = LaunchConfiguration('y_pose')
    z_pose = LaunchConfiguration('z_pose')


    # Launch Arguments
    world_name_launch_arg = DeclareLaunchArgument(
        'world_name',
        default_value='cones'
    )
    use_rviz_launch_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='True'
    )
    use_teleop_launch_arg = DeclareLaunchArgument(
        'use_teleop',
        default_value='True'
    )
    use_joystick_launch_arg = DeclareLaunchArgument(
        'use_joystick',
        default_value='False'
    )
    localization_launch_arg = DeclareLaunchArgument(
        'localization',
        default_value='False'
    )
    x_pose_launch_arg = DeclareLaunchArgument(
        'x_pose',
        default_value='0.0'
    )
    y_pose_launch_arg = DeclareLaunchArgument(
        'y_pose',
        default_value='0.0'
    )
    z_pose_launch_arg = DeclareLaunchArgument(
        'z_pose',
        default_value='1.0'
    )

    
    
    # Check if we're told to use sim time

    # Process the URDF file
    pkg_path = os.path.join(get_package_share_directory('ppp_bot'))
    models_dir = os.path.join(pkg_path, 'models')
    xacro_file = os.path.join(pkg_path, 'description', 'robot.urdf.xacro')
    slam_config_file = os.path.join(pkg_path, 'config', 'mapper_params_online_async.yaml')
    rviz_config_file = os.path.join(pkg_path, 'config', 'default.rviz')
    twist_mux_config_file = os.path.join(pkg_path, 'config', 'twist_mux.yaml')

    ign_launcher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_path, 'launch', 'launch_ign.launch.py')
        ]),
        launch_arguments={
            'world_name': world_name,
            'x_pose': x_pose,
            'y_pose': y_pose,
            'z_pose': z_pose
        }.items()
    )

    slam_launcher = IncludeLaunchDescription(
                        PythonLaunchDescriptionSource(
                            [os.path.join(pkg_path,
                                        'launch', 'online_async.launch.py')]),
                        launch_arguments={
                            'params_file': slam_config_file,
                            'use_sim_time': 'true'
                        }.items(),
                        condition=UnlessCondition(localization)
                    )

    

    rviz_node = Node(
            condition=IfCondition(use_rviz),
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config_file],
            parameters=[{'use_sim_time': True}]
        )


    twist_mux_node = Node(
            package='twist_mux',
            executable='twist_mux',
            parameters=[twist_mux_config_file, {'use_sim_time': True}],
            remappings=[('/cmd_vel_out', '/diff_drive_base_controller/cmd_vel_unstamped')]
        )

    navigation_launcher = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [os.path.join(pkg_path,
                              'launch', 'navigation.launch.py')]),
            launch_arguments={
                'use_sim_time': 'true',
                'params_file': os.path.join(pkg_path, 'config', 'nav2_params.yaml')
            }.items(),
            condition=IfCondition(localization)
        )

    delayed_rviz_nav = TimerAction(period=10.0, actions=[
        rviz_node,
        navigation_launcher
    ])
    
    
    keyboard_teleop = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_path, 'launch', 'keyboard.launch.py')
        ]),
        launch_arguments=[('use_sim_time', 'true')],
        condition=IfCondition(PythonExpression([
            use_teleop,
            ' and not ',
            use_joystick
        ]))
    )

    joystic_teleop = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_path, 'launch', 'joystick.launch.py')
        ]),
        launch_arguments=[('use_sim_time', 'true')],
        condition=IfCondition(PythonExpression([
            use_teleop,
            ' and ',
            use_joystick
        ]))
    )

    # Launch!
    return LaunchDescription([
        # Launch Arguments
        world_name_launch_arg,
        use_rviz_launch_arg,
        use_teleop_launch_arg,
        use_joystick_launch_arg,
        localization_launch_arg,
        x_pose_launch_arg,
        y_pose_launch_arg,
        z_pose_launch_arg,
        SetEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', models_dir),
        SetEnvironmentVariable('GTK_PATH', ''),

        ign_launcher,
        keyboard_teleop,
        joystic_teleop,
        slam_launcher,
        twist_mux_node,
        delayed_rviz_nav,
        OpaqueFunction(function=launch_localization, args=[world_name]),
    ])