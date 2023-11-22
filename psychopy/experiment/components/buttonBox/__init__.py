from pathlib import Path
from psychopy.experiment.components import BaseComponent, Param, getInitVals
from psychopy.localization import _translate


class ButtonBoxBackend:
    def __init_subclass__(cls, key, label=None):
        """
        Initialise a new backend for ButtonBoxComponent.

        Parameters
        ----------
        key : str
            Name of this backend - will be used in allowedVals for the deviceBackend parameter of ButtonBoxComponent.
            This will be used for indexing, so shouldn't be localized (translated)!
        label : str
            Label for this backend - will be used in allowedLabels for the deviceBackend parameter of
            ButtonBoxComponent.
        """
        # if not given a label, use key
        if label is None:
            label = key
        # store key and label in class
        cls.key = key
        cls.label = label
        # add class to list of backends for ButtonBoxComponent
        ButtonBoxComponent.backends.append(cls)

    def getParams(self):
        """
        Get parameters from this backend to add to each new instance of ButtonBoxComponent

        Returns
        -------
        dict[str:Param]
            Dict of Param objects, which will be added to any Button Box Component's params, along with a dependency
            to only show them when this backend is selected
        list[str]
            List of param names, defining the order in which params should appear
        """
        raise NotImplementedError()

    def addRequirements(self):
        """
        Add any required module/package imports for this backend
        """
        raise NotImplementedError()

    def writeInitCode(self, buff):
        raise NotImplementedError()


class ButtonBoxComponent(BaseComponent):
    """

    """
    categories = ['Responses']  # which section(s) in the components panel
    targets = ['PsychoPy']
    iconFile = Path(__file__).parent / 'buttonBox.png'
    tooltip = _translate('Button Box: Get input from a button box')
    # list of backends - starts with generic serial, plugins (lke psychopy-bbtk or psychopy-cedrus) will add to this
    backends = []

    def __init__(
            self, exp, parentName,
            # basic
            name='buttonBox', nButtons=1,
            startType='time (s)', startVal=0.0,
            stopType='duration (s)', stopVal=1.0,
            startEstim='', durationEstim='',
            forceEndRoutine=True,
            # device
            deviceName="",
            deviceBackend="serial",
            # data
            registerOn=True,
            allowedButtons="",
            # testing
            disabled=False,
            store='first key',
            useTimer=True,
            getReleaseTime=False,
            storeCorrect=False, correctAns="",

    ):
        # initialise base class
        BaseComponent.__init__(
            self, exp, parentName,
            name=name,
            startType=startType, startVal=startVal,
            stopType=stopType, stopVal=stopVal,
            startEstim=startEstim, durationEstim=durationEstim,
            disabled=disabled
        )

        self.exp.requireImport(
            importName="ButtonBox",
            importFrom="psychopy.hardware.button"
        )

        # --- Basic params ---
        self.order += [
            "nButtons"
        ]
        self.params['nButtons'] = Param(
            nButtons, valType="code", inputType="single", categ="Basic",
            label=_translate("Num. buttons"),
            hint=_translate(
                "How many butons this button box has."
            )
        )
        self.params['forceEndRoutine'] = Param(
            forceEndRoutine, valType='bool', inputType="bool", categ='Basic',
            hint=_translate(
                "Should a response force the end of the Routine (e.g end the trial)?"
            ),
            label=_translate("Force end of Routine"))

        # --- Data params ---
        self.order += [
            "registerOn",
            "allowedButtons",
        ]
        self.params['registerOn'] = Param(
            registerOn, valType='code', inputType='choice', categ='Data',
            allowedVals=[True, False],
            allowedLabels=[_translate("Press"), _translate("Release")],
            hint=_translate(
                "When should the button press be registered? As soon as pressed, or when released?"
            ),
            label=_translate("Register button press on...")
        )
        self.params['allowedButtons'] = Param(
            allowedButtons, valType='list', inputType="single", categ='Data',
            hint=_translate(
                "A comma-separated list of button indices (should be whole numbers), leave blank "
                "to listen for all buttons."
            ),
            label=_translate("Allowed buttons"))

        # --- Device params ---
        self.order += [
            "deviceName",
            "deviceBackend",
        ]
        # activate plugins so backends are available
        from psychopy.plugins import activatePlugins
        activatePlugins()
        self.params['deviceName'] = Param(
            deviceName, valType="str", inputType="single", categ="Device",
            label=_translate("Device name"),
            hint=_translate(
                "A name to refer to this Component's associated hardware device by. If using the "
                "same device for multiple components, be sure to use the same name here."
            )
        )
        self.params['deviceBackend'] = Param(
            deviceBackend, valType="str", inputType="choice", categ="Device",
            allowedVals=[getattr(cls, 'key', cls.__name__) for cls in self.backends],
            allowedLabels=[getattr(cls, 'label', cls.__name__) for cls in self.backends],
            label=_translate("Device backend"),
            hint=_translate(
                "What kind of button box is it? What package/plugin should be used to talk to it?"
            ),
            direct=False
        )

        # add params from backends
        for backend in self.backends:
            # get params using backend's method
            params, order = backend.getParams(self)
            # add params and order
            self.params.update(params)
            self.order.extend(order)
            # add dependencies
            for name in params:
                self.depends.append(
                    {
                        "dependsOn": "deviceBackend",  # if...
                        "condition": f"== '{backend.key}'",  # meets...
                        "param": name,  # then...
                        "true": "show",  # should...
                        "false": "hide",  # otherwise...
                    }
                )
            # add requirements
            backend.addRequirements(self)

    def writeDeviceCode(self, buff):
        # write init code from backend
        for backend in self.backends:
            if backend.key == self.params['deviceBackend']:
                backend.writeDeviceCode(self, buff)

    def writeInitCode(self, buff):
        inits = getInitVals(self.params)
        # code to create object
        code = (
            "%(name)s = ButtonBox(\n"
            "    device=%(deviceName)s\n"
            ")\n"
        )
        buff.writeIndentedLines(code % inits)

    def writeFrameCode(self, buff):
        params = self.params
        code = (
            "\n"
            "# *%(name)s* updates\n"
        )
        buff.writeIndentedLines(code % params)
        # writes an if statement to determine whether to draw etc
        indented = self.writeStartTestCode(buff)
        if indented:
            # dispatch and clear messages
            code = (
                "# clear any messages from before starting\n"
                "%(name)s.responses = []\n"
                "%(name)s.clearResponses()\n"
            )
            buff.writeIndentedLines(code % params)
            # to get out of the if statement
            buff.setIndentLevel(-indented, relative=True)

        # test for started (will update parameters each frame as needed)
        indented = self.writeActiveTestCode(buff)
        if indented:
            # write code to get messages
            code = (
                "# ask for messages from %(name)s device this frame\n"
                "for resp in %(name)s.getResponses(\n"
                "    state=%(registerOn)s, channel=%(allowedButtons)s, clear=True\n"
                "):\n"
                "    %(name)s.buttons.append(resp.channel)\n"
                "    %(name)s.times.append(resp.t)\n"
            )
            buff.writeIndentedLines(code % params)
            # code to end Routine
            if self.params['forceEndRoutine']:
                code = (
                    "# end Routine if %(name)s got valid response\n"
                    "if len(%(name)s.buttons):\n"
                    "    continueRoutine = False\n"
                )
                buff.writeIndentedLines(code % params)

            # to get out of the if statement
            buff.setIndentLevel(-indented, relative=True)

        # test for stop (only if there was some setting for duration or stop)
        indented = self.writeStopTestCode(buff)
        if indented:
            # to get out of the if statement
            buff.setIndentLevel(-indented, relative=True)

    def writeRoutineEndCode(self, buff):
        BaseComponent.writeRoutineEndCode(self, buff)
        params = self.params

        # write code to save responses
        code = (
            "# store data from %(name)s\n"
            "thisExp.addData('%(name)s.buttons', %(name)s.buttons)\n"
            "thisExp.addData('%(name)s.times', %(name)s.times)\n"
        )
        buff.writeIndentedLines(code % params)


class SerialButtonBoxBackend(ButtonBoxBackend, key="serial", label=_translate("Generic serial")):
    """
    Adds a basic serial connection backend for ButtonBoxComponent, as well as acting as an example for implementing
    other ButtonBoxBackends.
    """
    def getParams(self: ButtonBoxComponent):
        # define order
        order = [
            "serialPort",
            "serialBaudRate",
            "serialByteSize",
            "serialParity"
        ]
        # define params
        params = {}
        from psychopy.hardware.serialdevice import _findPossiblePorts
        params['serialPort'] = Param(
            "", valType="str", inputType="choice", categ="Device",
            allowedVals=_findPossiblePorts,
            label=_translate("COM port"),
            hint=_translate(
                "Serial port to connect to"
            )
        )
        params['serialBaudRate'] = Param(
            9600, valType='int', inputType="single", categ='Device',
            label=_translate("Baud rate"),
            hint=_translate(
                "The baud rate, or speed, of the connection."
            )
        )
        params['serialByteSize'] = Param(
            8, valType='int', inputType="single", categ='Device',
            label=_translate("Byte size"),
            hint=_translate(
                "How many bits are in each byte sent by the button box?"
            )
        )
        params['serialParity'] = Param(
            "N", valType='str', inputType="choice", categ='Device',
            allowedVals=('N', 'E', 'O', 'M', 'S'),
            allowedLabels=("None", "Even", "Off", "Mark", "Space"),
            label=_translate("Parity"),
            hint=_translate(
                "Parity mode for the button box device."
            )
        )

        return params, order

    def addRequirements(self: ButtonBoxComponent):
        self.exp.requireImport(
            importName="button", importFrom="psychopy.hardware"
        )

    def writeInitCode(self: ButtonBoxComponent, buff):
        # get inits
        inits = getInitVals(self.params)
        # make Keyboard object
        code = (
            "%(name)s = button.SerialButtonBox(\n"
            "    name=%(name)s,\n"
            "    buttons=%(nButtons)s,\n"
            "    port=%(serialPort)s,\n"
            "    baudrate=%(serialBaudRate)s,\n"
            "    byteSize=%(serialByteSize)s,\n"
            "    parity=%(serialParity)s,\n"
            ")\n"
        )
        buff.writeIndentedLines(code % inits)
