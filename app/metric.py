def serialize_labels(labels):
  if not labels:
    return ""

  inside = ', '.join([f"{key}=\"{val}\"" for (key, val) in labels.items()])
  return '{' + inside + '}'

class Metric:
  help_text = None
  metric_name = None
  metric_type = None
  # value = None

  def __init__(self, metric_name, metric_type, help_text):
    self.metric_name = metric_name
    self.metric_type = metric_type
    self.help_text = help_text

  def print_metrics(self, value, labels = {}):
    # if new_value:
    #   self.value = new_value

    return self.print_help_text() + self.print_value_text(value, labels)

  def print_help_text(self):
    return [
      f"# HELP {self.metric_name} {self.help_text}",
      f"# TYPE {self.metric_name} {self.metric_type}"
    ]

  def print_value_text(self, value, labels = {}):
    # if new_value:
    #   self.value = new_value

    return [f"{self.metric_name}{serialize_labels(labels)} {value or 0}"]
    

  def set_value(self, v):
    self.value = v

class Gauge(Metric):
  metric_type = "gauge"

  def __init__(self, metric_name, help_text):
    self.metric_name = metric_name
    self.help_text = help_text

class Counter(Metric):
  metric_type = "counter"

  def __init__(self, metric_name, help_text):
    self.metric_name = metric_name
    self.help_text = help_text