# Copyright 2020 University of Chicago
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ironic_python_agent import hardware
from oslo_log import log

LOG = log.getLogger()


class ChameleonHardwareManager(hardware.HardwareManager):

    HARDWARE_MANAGER_NAME = 'ChameleonHardwareManager'
    HARDWARE_MANAGER_VERSION= '1'

    def evaluate_hardware_support(self)
        return hardware.HardwareSupport.SERVICE_PROVIDER

    def get_clean_steps(self, node, ports):
	    """Get a list of clean steps with priority.
        :param node: The node object as provided by Ironic.
		:param ports: Port objects as provided by Ironic.
		:returns: A list of cleaning steps, as a list of dicts.
		"""
		return [{
					'step': 'get_node_info',
					'priority': 90,
					'interface': 'deploy',
					'reboot_requested': False,
					'abortable': True
                },
                {
                    'step': 'wait_debug',
                    'priority': 90,
                    'interface': 'deploy',
                    'abortable': True
                }]


    def wait_debug(self, node, ports):
		"""Holds the IPA for 30 minutes to inspect the state of the ramdisk.
		:param node: A dictionary of the node object
		:param ports: A list of dictionaries containing information of ports
					for the node
		"""
		LOG.warning("Waiting 30 minutes for interactive debugging ....")
		time.sleep(60 * 30)


	def get_node_info(self):
		"""Return full hardware inventory as a dict.
		:returns: A dictionary representing inventory
		"""
		hardware_info = super(ChameleonHardwareManager, self).get_hardware_info()
		hardware_info = self.
		output = get_lshw_data()
		hw_info = json.loads(output)
		hw_json = {"system" : get_system_info(hw_info),
			"openstack" : get_openstack_info(),
			"cpu" : get_cpu_info(hw_info),
			"memory" : get_mem_info(hw_info),
			"nic" : get_nic_info(hw_info),
			"disk" : get_disk_info(hw_info),
			"power" : get_power_info(hw_info),
			"gpu" : get_gpu_info(hw_info),
			"fpga" : get_fpga_info(hw_info)}
        tftp 192.0.2.135 <<fin
        put testfile2.txt
        quit
        fin
		#return hw_json        

		def get_lshw_data():
		    lshw_output = subprocess.Popen(["lshw", "-json"], stdout=subprocess.PIPE)
		    return lshw_output.communicate()[0]

		def find_attribute(hw_info, attribute, user_input):
			for entry in hw_info.get("children", []):
				if entry.get(attribute) == user_input.strip():
					yield entry
				for child in find_attribute(entry, attribute, user_input):
					yield child

		def get_nic_info(hw_info):
			nic_info_dict = {}
			counter = 0
			for nic in find_class(hw_info, "network"):
				nic_info_dict[counter] = {}
				nic_info_dict[counter]["name"] = nic["logicalname"]
				nic_info_dict[counter]["driver"] = nic["configuration"]["driver"]
				nic_info_dict[counter]["type"] = nic["description"]
				nic_info_dict[counter]["serial"] = nic["serial"]
				if 'product' in nic:
					nic_info_dict[counter]["model"] = nic["product"]
				if 'vendor' in nic:
					nic_info_dict[counter]["vendor"] = nic["vendor"]
				if 'link' in nic["configuration"].keys():
					nic_info_dict[counter]["wired"] = nic["configuration"]["link"]
				if 'speed' in nic["configuration"].keys():
					nic_info_dict[counter]["speed"] = nic["configuration"]["speed"]
				if nic_info_dict[counter]["name"] == "ib0":
					ib_speed_match = re.search("Speed:.*", (subprocess.run(["ethtool", "ib0"], stdout=subprocess.PIPE, universal_newlines=True).stdout))
					nic_info_dict[counter]["speed"] = ib_speed_match.group().split(": ")[1]
				counter += 1
			return nic_info_dict

		def get_disk_info(hw_info):
			disk_info_dict = {}
			counter = 0
			blk_output = subprocess.Popen(["lsblk", "-b", "-d", "-O", "--json"], stdout=subprocess.PIPE)
			lsblk_output = blk_output.communicate()[0]
			lsblk_json = json.loads(lsblk_output)
			for disk in lsblk_json["blockdevices"]:
				if disk["type"] == "disk":
					disk_info_dict[counter] = {}
					disk_info_dict[counter]["name"] = disk["name"]
					disk_info_dict[counter]["size"] = disk["size"]
					disk_info_dict[counter]["model"] = disk["model"].rstrip()
					disk_info_dict[counter]["serial"] = disk["serial"]
					for i in find_attribute(hw_info, "product", disk_info_dict[counter]["model"]):
						if "vendor" in i:
							disk_info_dict[counter]["vendor"] = i["vendor"]
			## Tried to fix edge case for when vendor is generic i.e. "Linux" but results in "ATA" for Intel SSDs.
			## Could lead to other issues since it overwrites lshw vendor info 
						# else:
						#   print(disk["vendor"].rstrip())
						#  disk_info_dict[counter]["vendor"] = disk["vendor"].rstrip()
					disk_info_dict[counter]["interface"] = disk["tran"]
					disk_info_dict[counter]["rev"] = disk["rev"]
					driver_output = subprocess.run(["udevadm", "info", "-a", "-n", disk["name"]],stdout=subprocess.PIPE,universal_newlines=True)
					# print(driver_output.stdout)
					match = re.findall(r'DRIVERS=="(\w+)"', driver_output.stdout)
					if match:
						if "pcieport" in match: #filter out pcieport drivers
							drivers = [x for x in match if x != "pcieport"]
						disk_info_dict[counter]["driver"] = drivers
					counter +=1
			return disk_info_dict

		def get_mem_info(hw_info):
			mem_info_dict = {}
			counter = 0
			for mem in find_class(hw_info, "memory"):
				if (mem["id"] == "memory"):  # Total Memory
					if 'size' in mem:
						mem_info_dict["total_mem"] = ("{} GiB".format(mem["size"]/1024/1024/1024))
				if ( "bank" in mem["id"] ): # Individual DIMMs
					if (mem["description"] != "[empty]"):
						mem_info_dict[counter] = {}
						mem_info_dict[counter]["slot"] = mem["slot"]
						mem_info_dict[counter]["type"] = mem["description"]
						mem_info_dict[counter]["size"] = "{} GiB".format(mem["size"]/1024/1024/1024)
						mem_info_dict[counter]["clock"] = "{} MHz".format(mem["clock"]/1000/1000)
					counter += 1
			return mem_info_dict
			
		def get_cpu_info(hw_info):
			counter = 0
			cpu_info_dict = {}
			lscpu_output = subprocess.run(["lscpu"], stdout=subprocess.PIPE, universal_newlines=True)
			max_clock_match = re.search("CPU max MHz.*", lscpu_output.stdout)
			architecture_match = re.search("Architecture:.*", lscpu_output.stdout)
			for cpu in find_class(hw_info, "processor"): #individual CPUs
				cpu_info_dict[counter] = {}
				cpu_info_dict[counter]["product"] = cpu["product"].split(" @ ")[0] #May be Intel specific
				cpu_info_dict[counter]["vendor"] = cpu["vendor"]
				cpu_info_dict[counter]["threads"] = cpu["configuration"]["threads"]
				cpu_info_dict[counter]["cores"] = cpu["configuration"]["cores"]
				cpu_info_dict[counter]["architecture"] = architecture_match.group().split()[1] 
				cpu_info_dict[counter]["level1_cache"] = "{} Bytes".format((subprocess.run(["getconf",  "LEVEL1_DCACHE_SIZE"], stdout=subprocess.PIPE, universal_newlines=True)).stdout.rstrip())
				cpu_info_dict[counter]["level2_cache"] = "{} Bytes".format((subprocess.run(["getconf",  "LEVEL2_CACHE_SIZE"], stdout=subprocess.PIPE, universal_newlines=True)).stdout.rstrip())
				cpu_info_dict[counter]["level3_cache"] = "{} Bytes".format((subprocess.run(["getconf",  "LEVEL3_CACHE_SIZE"], stdout=subprocess.PIPE, universal_newlines=True)).stdout.rstrip())
				cpu_info_dict[counter]["max_freq"] = "{} GHz".format(int(max_clock_match.group().split()[3].split(".")[0])/1000)
				cpu_info_dict[counter]["base_freq"] = "{} GHz".format(cpu["product"].split(" @ ")[1].split("G")[0]) #May be Intel specific
				#cpu_info_dict["total_threads"] += int(cpu["configuration"]["threads"])
				counter += 1
			cpu_info_dict["total_threads"] = int(cpu_info_dict[0]["threads"]) * counter
			cpu_info_dict["cpu_count"] = counter
			return cpu_info_dict

		def get_power_info(hw_info):
			psu_info_dict = {}
			counter = 0
			for psu in find_class(hw_info, "power"):
				psu_info_dict[counter] = {}
				if 'serial' in psu:
					psu_info_dict[counter]["serial"] = psu["serial"]
				if 'serial' in psu:
					psu_info_dict[counter]["product"] = psu["product"]
				psu_info_dict[counter]["vendor"] = psu["vendor"]
				psu_info_dict[counter]["capacity"] = str(psu["capacity"]) + " " + str(psu["units"])
				#psu_info_dict[counter]["slot"] = psu["physid"]
				counter += 1
			return psu_info_dict

		def get_system_info(hw_info):
			system_info_dict = {}
			system_info_dict["bios_info"] = {}
			# for sysinfo in find_class(hw_info, ""):
			# system_info_dict["model"] = hw_info["product"]
			system_info_dict["vendor"] = hw_info["vendor"]
			if system_info_dict["vendor"] == "Dell Inc.":
				system_info_dict["model"] = hw_info["product"].split("(SKU=NotProvided")[0].strip()
			system_info_dict["serial"] = hw_info["serial"]
			system_info_dict["bios_info"]["version"] = hw_info["children"][0]["children"][0]["version"]
			system_info_dict["bios_info"]["release_date"] = hw_info["children"][0]["children"][0]["date"]
			return system_info_dict

		def get_gpu_info(hw_info):
			gpu_info_dict = {}
			counter = 0
			for gpu in find_class(hw_info, "display"):
				#print(gpu["description"])
				#print(re.search("VGA", gpu["description"])) 
				if not re.search("VGA", gpu["description"]) :
					gpu_info_dict[counter] = {}
					gpu_info_dict[counter]["model"] = gpu["product"]
					counter += 1
			gpu_info_dict["total_num_gpus"] = counter
			return gpu_info_dict

		def get_fpga_info(hw_info):
			counter = 0
			fpga_info_dict = {}
			for fpga in find_class(hw_info,"generic"):
				if fpga["vendor"] == "Altera Corporation":
					fpga_info_dict["FPGA"] = True
					counter +=1
				return fpga_info_dict
