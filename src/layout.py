from wtfj import*

class Layout(Piece):

	def _BEFORE_start(self):
		self.subscribe(Uid.ENGINE)
		self.subscribe(Uid.EYETRACKER)
		self.subscribe(Uid.BLINK)
		self.subscribe(Uid.TEXT)
		self.subscribe(Uid.WFACE)
		self._horizontal_division = False
		self._n_current_keys = 0
		self._last_eye2 = (0,0,0.0)
		self._last_eye1 = (0,0,0.0)
		self._last_eye = (0.0,0.0)
		self._imagenames = {}
		self._last_feedback_key = '-1,-1,-1,-1'

	def _ON_text_buffer(self,data):
		self.send_to(Uid.TKPIECE,Msg.TEXT,'feedback'+','+data)

	def _ON_eyetracker_gaze(self,data):
		'''Only record a single gaze coordinate at a time.'''
		eye_data = data.split(",")
		self._last_eye = (float(eye_data[0]),float(eye_data[1]))
		self._last_eye2 = self._last_eye1
		self._last_eye1 = self._last_eye
		self._last_eye = ((self._last_eye1[0]+self._last_eye2[0])/2, (self._last_eye1[1] + self._last_eye2[1])/2) # Average of last two gaze points
		self._generate_feedback()
	
	def _generate_feedback(self):
		'''Provides audio and visual feedback when the user has entered a new selectiona area.'''
		shapes = self.shape_list.split(",")
		for index in range(0,len(shapes)/5):
			ul = (shapes[5*index+1],shapes[5*index+2])
			br = (shapes[5*index+3],shapes[5*index+4])
			coord_string = str(ul[0]) + ',' + str(ul[1]) + ',' + str(br[0]) + ',' + str(br[1])
			if (self._contains(ul,br) == True):
				if (coord_string != self._last_feedback_key):
					# Visual feedback goes directly to tkpiece
					self.send_to(Uid.TKPIECE,Msg.FEEDBACK, coord_string)
					# Audio feedback is routed through engine to audio
					self.send_to(Uid.ENGINE,Msg.FEEDBACK, str(index))
					self._last_feedback_key = coord_string

	def _contains(self,upper_left, bottom_right):
		'''Helper function to determine if a shape contains the last
		eyetracker coordinates.'''
		# Until screen size is dynamic on eyetracker:
		ul = (float(upper_left[0]),float(upper_left[1]))
		br = (float(bottom_right[0]),float(bottom_right[1]))
		if (ul[0] < self._last_eye[0] and ul[1] < self._last_eye[1] and br[0] > self._last_eye[0] and br[1] > self._last_eye[1]):
			return True
		return False

	def _check_select(self):
		shapes = self.shape_list.split(",")
		for index in range(0,len(shapes)/5):
			ul = (shapes[5*index+1],shapes[5*index+2])
			br = (shapes[5*index+3],shapes[5*index+4])
			if (self._contains(ul,br) == True):
				self.send_to(Uid.ENGINE,Msg.SELECT,str(index))

	def _ON_blink_select(self,data):
		'''When a blink select signal is emitted, check if the last
		eye coordinate was within any of the keys'''
		self._check_select()

	def _ON_wface_select(self,data):
		'''When a face select signal is emitted, check if the last
		eye coordinate was within any of the keys'''
		self._check_select()

	def _clear_screen(self):
		'''Before drawing anything on the screen, clear all images and keys'''
		for i in range(self._n_current_keys):
			self.send_to(Uid.TKPIECE,Req.DELETE,'key'+str(i))
		num_keys = 0
		for key in self._imagenames:
			self.send_to(Uid.TKPIECE,Req.DELETE,self._imagenames[key])
			num_keys += 1
		for i in range(num_keys):
			try:
				del self._imagenames[i]
			except KeyError:
				pass # No key present yet
		self._n_current_keys = 0

	def _divide_screen(self,n,options):
		'''Helper method that determines how to divide the screen between the number of keys (n) on the screen'''
		max_rows = 5
		shape_type = "rect"
		assert(max_rows == 5)
		if (n > max_rows):
			cols = n/max_rows + (n%max_rows > 0)
		elif(n == max_rows):
			cols = n/(max_rows/2) + (n%(max_rows/2) > 0) - 1
		else:
			if (self._horizontal_division == False and n == 2):
				cols = 2;
			else:
				cols = n/2 + (n%2 > 0)
		col_keys = []
		for x in range(cols):
			col_keys.append(1)
		i = 0
		while(sum(col_keys) != n):
			col_keys[i%len(col_keys)] += 1
			i+=1

		self.shape_list = ""
		dx = 1.0 / (len(col_keys))
		i = 0
		key_counter = 0
		for val in reversed(col_keys):
			dy = .85 / (val)
			j = 1
			for x in range(0,val):
				ul = (i*dx,x*dy)
				br = (min(1,(i+1)*dx),min(1,(x+1)*dy))
				self.shape_list = self.shape_list + shape_type + "," + str(ul[0]) + "," + str(ul[1]) + "," + str(br[0]) + "," + str(br[1]) + ","
				x = (ul[0] + br[0])/2
				y = (ul[1] + br[1])/2
				# Handle images
				if options[key_counter][0] == '#':
					option = options[key_counter]
					option = option[1:]
					# Save the image handle as the option name
					self._imagenames[key_counter] = option
					# Create and draw the image
					self.send_to(Uid.TKPIECE,Req.IMAGE,option+','+str(x)+','+str(y))
				# Handle Text
				else:			
					self.send_to(Uid.TKPIECE,Req.CREATE,'text,key'+str(key_counter)+','+str(x)+','+str(y))
					# Update the value of the text field
					options[key_counter] = options[key_counter].replace('_to_',':')
					self.send_to(Uid.TKPIECE,Msg.TEXT,'key'+str(key_counter)+','+options[key_counter])
				j+=1
				key_counter += 1
			i+=1
		self.shape_list = self.shape_list[0:len(self.shape_list)-1]

	def _ON_engine_options(self,data):
		options = data.split(',')
		# Find neumber of options emitted by engine
		n = len(options)
		# If those options differ from the current number of options clear the screen of options
		self._clear_screen()
		self._divide_screen(n,options)

		# Save current number of options displayed and send acknowledgement back				
		self._n_current_keys = n
		self.send(Msg.ACK)

	@staticmethod
	def script():
		text_entry = [
			'@layout marco',
			'engine options a_to_i,j_to_r,s_to_z',
			'eyetracker gaze .4,.5',
			'engine options spc,com,.',
			'eyetracker gaze .4,.5',
			'eyetracker gaze .75,.3',
			'@engine stop'
		]
		return Script(text_entry)

if __name__ == '__main__':
	from sys import argv
	Runner.run_w_cmd_args(Layout,argv)